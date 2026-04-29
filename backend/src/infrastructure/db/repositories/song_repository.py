"""SQLAlchemy implementation of ``SongRepository``.

Read-side methods (search_summary_views, get_detail_view) implement T063.
Write-side methods (add, update_with_version, delete_with_version,
find_by_dedup_key) are filled in by Phase 4 (T092).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from uuid import uuid4

from sqlalchemy import Select, and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Composer, Song, SongOptionalLink
from src.domain.errors import (
    DuplicateSongError,
    VersionConflictError,
)
from src.domain.queries.song_views import (
    ComposerView,
    OptionalFieldValueView,
    SongDetailView,
    SongSummaryPage,
    SongSummaryView,
    TaxonomyValueView,
)
from src.domain.repositories import (
    Pagination,
    SongFilters,
    SongPage,
    SongRepository,
)
from src.domain.value_objects import DedupKey, LinkUrl, TaxonomyKind
from src.infrastructure.db.models import (
    ComposerModel,
    OptionalFieldDefinitionModel,
    SongComposerLink,
    SongModel,
    SongOptionalFieldValueModel,
    SongTaxonomyValueLink,
    TaxonomyValueModel,
)

__all__ = ["SqlAlchemySongRepository"]


class SqlAlchemySongRepository(SongRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ----- write-side (T092) ----------------------------------------------
    async def get_by_id(self, song_id: UUID) -> Song | None:
        row = await self._session.get(SongModel, song_id)
        if row is None:
            return None
        # Hydrate composer ids + names.
        comp_stmt = (
            select(ComposerModel.id, ComposerModel.name, ComposerModel.name_norm)
            .join(SongComposerLink, SongComposerLink.composer_id == ComposerModel.id)
            .where(SongComposerLink.song_id == song_id)
        )
        comp_rows = (await self._session.execute(comp_stmt)).all()
        composer_ids = frozenset(r[0] for r in comp_rows)
        composer_names = tuple(r[1] for r in comp_rows)
        # Taxonomy ids
        tax_stmt = select(SongTaxonomyValueLink.taxonomy_value_id).where(
            SongTaxonomyValueLink.song_id == song_id
        )
        taxonomy_value_ids = frozenset(
            (await self._session.execute(tax_stmt)).scalars().all()
        )
        # Optional links
        opt_stmt = select(
            SongOptionalFieldValueModel.definition_id,
            SongOptionalFieldValueModel.value_url,
        ).where(SongOptionalFieldValueModel.song_id == song_id)
        opt_rows = (await self._session.execute(opt_stmt)).all()
        optional_links = tuple(
            SongOptionalLink(definition_id=def_id, value=LinkUrl(value=url))
            for def_id, url in opt_rows
        )
        return Song(
            id=row.id,
            title=row.title,
            composer_ids=composer_ids,
            composer_names=composer_names,
            taxonomy_value_ids=taxonomy_value_ids,
            optional_links=optional_links,
            dedup_key=DedupKey(value=row.dedup_key),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            updated_by=row.updated_by,
            version=row.version,
        )

    async def find_by_dedup_key(self, dedup_key: DedupKey) -> Song | None:
        row = (
            await self._session.execute(
                select(SongModel).where(SongModel.dedup_key == dedup_key.value)
            )
        ).scalar_one_or_none()
        return await self.get_by_id(row.id) if row else None

    async def find_composer_by_norm(self, name_norm: str) -> Composer | None:
        stmt = select(ComposerModel).where(ComposerModel.name_norm == name_norm)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return Composer(
            id=row.id, name=row.name, name_norm=row.name_norm, created_at=row.created_at
        )

    async def search(self, filters: SongFilters, pagination: Pagination) -> SongPage:
        # Less commonly used than search_summary_views; here for ABC parity.
        # Returns Song entities (no hydrated composer / taxonomy detail).
        stmt = (
            self._build_filtered_song_select(filters)
            .order_by(SongModel.updated_at.desc())
            .offset(pagination.offset())
            .limit(pagination.page_size)
        )
        rows = (await self._session.execute(stmt)).all()
        items: list[Song] = []
        for row in rows:
            song = await self.get_by_id(row[0])
            if song is not None:
                items.append(song)
        total = (
            await self._session.execute(
                select(func.count()).select_from(
                    self._build_filtered_song_select(filters).subquery()
                )
            )
        ).scalar_one()
        return SongPage(
            items=items, total=total, page=pagination.page, page_size=pagination.page_size
        )

    async def add(self, song: Song, *, composers: list[Composer]) -> None:
        # Persist composers first (find-or-create already happened upstream).
        for composer in composers:
            await self._upsert_composer(composer)
        self._session.add(
            SongModel(
                id=song.id,
                title=song.title,
                dedup_key=song.dedup_key.value,
                created_at=song.created_at,
                updated_at=song.updated_at,
                created_by=song.created_by,
                updated_by=song.updated_by,
                version=song.version,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            existing = await self.find_by_dedup_key(song.dedup_key)
            if existing is not None and existing.id != song.id:
                raise DuplicateSongError(
                    "A song with the same title and composer set already exists",
                    conflicting_song_id=existing.id,
                ) from exc
            raise
        for composer in composers:
            self._session.add(
                SongComposerLink(song_id=song.id, composer_id=composer.id)
            )
        for tv_id in song.taxonomy_value_ids:
            self._session.add(
                SongTaxonomyValueLink(song_id=song.id, taxonomy_value_id=tv_id)
            )
        for link in song.optional_links:
            self._session.add(
                SongOptionalFieldValueModel(
                    id=uuid4(),
                    song_id=song.id,
                    definition_id=link.definition_id,
                    value_url=link.value.value,
                    created_at=song.created_at,
                    updated_at=song.updated_at,
                )
            )
        await self._session.flush()

    async def update_with_version(
        self, song: Song, *, composers: list[Composer], expected_version: int
    ) -> None:
        # Conditional UPDATE on the songs row.
        result = await self._session.execute(
            update(SongModel)
            .where(
                SongModel.id == song.id, SongModel.version == expected_version
            )
            .values(
                title=song.title,
                dedup_key=song.dedup_key.value,
                updated_at=song.updated_at,
                updated_by=song.updated_by,
                version=song.version,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise VersionConflictError(expected_version=expected_version)

        # Replace child associations (composers, taxonomies, optional fields).
        # Composers: delete all existing links and re-add (cheap at our scale).
        await self._session.execute(
            delete(SongComposerLink).where(SongComposerLink.song_id == song.id)
        )
        for composer in composers:
            await self._upsert_composer(composer)
            self._session.add(
                SongComposerLink(song_id=song.id, composer_id=composer.id)
            )

        await self._session.execute(
            delete(SongTaxonomyValueLink).where(
                SongTaxonomyValueLink.song_id == song.id
            )
        )
        for tv_id in song.taxonomy_value_ids:
            self._session.add(
                SongTaxonomyValueLink(song_id=song.id, taxonomy_value_id=tv_id)
            )

        await self._session.execute(
            delete(SongOptionalFieldValueModel).where(
                SongOptionalFieldValueModel.song_id == song.id
            )
        )
        for link in song.optional_links:
            self._session.add(
                SongOptionalFieldValueModel(
                    id=uuid4(),
                    song_id=song.id,
                    definition_id=link.definition_id,
                    value_url=link.value.value,
                    created_at=song.updated_at,
                    updated_at=song.updated_at,
                )
            )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            existing = await self.find_by_dedup_key(song.dedup_key)
            if existing is not None and existing.id != song.id:
                raise DuplicateSongError(
                    "A song with the same title and composer set already exists",
                    conflicting_song_id=existing.id,
                ) from exc
            raise

    async def delete_with_version(
        self, song_id: UUID, *, expected_version: int
    ) -> None:
        result = await self._session.execute(
            delete(SongModel).where(
                SongModel.id == song_id, SongModel.version == expected_version
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise VersionConflictError(expected_version=expected_version)

    async def _upsert_composer(self, composer: Composer) -> None:
        # Insert if missing (id-based). Composer rows are immutable in v1.
        existing = await self._session.get(ComposerModel, composer.id)
        if existing is not None:
            return
        # Possible name_norm collision if the upstream find-or-create raced.
        norm_match = (
            await self._session.execute(
                select(ComposerModel).where(ComposerModel.name_norm == composer.name_norm)
            )
        ).scalar_one_or_none()
        if norm_match is not None:
            return
        self._session.add(
            ComposerModel(
                id=composer.id,
                name=composer.name,
                name_norm=composer.name_norm,
                created_at=composer.created_at,
            )
        )

    # ----- read-side (T063) -----------------------------------------------
    async def search_summary_views(
        self, filters: SongFilters, pagination: Pagination
    ) -> SongSummaryPage:
        # Build a base query that applies the q + taxonomy filters.
        base = self._build_filtered_song_select(filters)

        # Total before pagination.
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Get the paged song IDs ordered by recency.
        page_song_id_stmt = (
            select(SongModel.id, SongModel.updated_at, SongModel.title, SongModel.version)
            .select_from(base.subquery().alias("filtered"))
        )
        # Re-build with proper select on SongModel for ORDER BY:
        ordered = (
            self._build_filtered_song_select(filters)
            .order_by(SongModel.updated_at.desc())
            .offset(pagination.offset())
            .limit(pagination.page_size)
        )
        rows = (await self._session.execute(ordered)).all()
        if not rows:
            return SongSummaryPage(
                items=[], total=total, page=pagination.page, page_size=pagination.page_size
            )
        song_ids = [r[0] for r in rows]

        composers_by_song = await self._fetch_composers_by_songs(song_ids)
        taxonomies_by_song = await self._fetch_taxonomies_by_songs(song_ids)

        # Order composers / taxonomies inside each song deterministically.
        items: list[SongSummaryView] = []
        for row in rows:
            song_id, _updated_at, title, version = row[0], row[1], row[2], row[3]
            tax_for_song = taxonomies_by_song.get(song_id, [])
            seasons, masses, special = _split_taxonomies_by_kind(tax_for_song)
            items.append(
                SongSummaryView(
                    id=song_id,
                    title=title,
                    composers=tuple(composers_by_song.get(song_id, [])),
                    seasons=tuple(seasons),
                    masses=tuple(masses),
                    special_events=tuple(special),
                    version=version,
                )
            )
        return SongSummaryPage(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_detail_view(self, song_id: UUID) -> SongDetailView | None:
        song_row = (
            await self._session.execute(select(SongModel).where(SongModel.id == song_id))
        ).scalar_one_or_none()
        if song_row is None:
            return None

        composers_by_song = await self._fetch_composers_by_songs([song_id])
        taxonomies_by_song = await self._fetch_taxonomies_by_songs([song_id])
        seasons, masses, special = _split_taxonomies_by_kind(
            taxonomies_by_song.get(song_id, [])
        )

        opt_stmt = (
            select(SongOptionalFieldValueModel, OptionalFieldDefinitionModel.label)
            .join(
                OptionalFieldDefinitionModel,
                OptionalFieldDefinitionModel.id == SongOptionalFieldValueModel.definition_id,
            )
            .where(SongOptionalFieldValueModel.song_id == song_id)
            .order_by(OptionalFieldDefinitionModel.label)
        )
        opt_rows = (await self._session.execute(opt_stmt)).all()
        optional_fields = tuple(
            OptionalFieldValueView(
                definition_id=row[0].definition_id,
                label=row[1],
                value_url=row[0].value_url,
            )
            for row in opt_rows
        )

        return SongDetailView(
            id=song_row.id,
            title=song_row.title,
            composers=tuple(composers_by_song.get(song_id, [])),
            seasons=tuple(seasons),
            masses=tuple(masses),
            special_events=tuple(special),
            optional_fields=optional_fields,
            version=song_row.version,
            created_at=song_row.created_at,
            updated_at=song_row.updated_at,
        )

    # ----- helpers --------------------------------------------------------
    def _build_filtered_song_select(self, filters: SongFilters) -> Select:
        """Build a SELECT against ``songs`` that applies the q + taxonomy filters."""

        stmt = select(
            SongModel.id, SongModel.updated_at, SongModel.title, SongModel.version
        )

        # Composer name search uses pg_trgm; same expression used for title.
        if filters.q:
            term = f"%{filters.q.strip().lower()}%"
            composer_search = (
                select(SongComposerLink.song_id)
                .join(ComposerModel, ComposerModel.id == SongComposerLink.composer_id)
                .where(func.lower(ComposerModel.name).like(term))
            )
            stmt = stmt.where(
                or_(
                    func.lower(SongModel.title).like(term),
                    SongModel.id.in_(composer_search),
                )
            )

        for kind, ids in filters.taxonomy_value_ids_by_kind.items():
            if not ids:
                continue
            sub = (
                select(SongTaxonomyValueLink.song_id)
                .join(
                    TaxonomyValueModel,
                    TaxonomyValueModel.id == SongTaxonomyValueLink.taxonomy_value_id,
                )
                .where(
                    and_(
                        TaxonomyValueModel.kind == kind.value,
                        SongTaxonomyValueLink.taxonomy_value_id.in_(list(ids)),
                    )
                )
            )
            stmt = stmt.where(SongModel.id.in_(sub))

        return stmt

    async def _fetch_composers_by_songs(
        self, song_ids: Iterable[UUID]
    ) -> dict[UUID, list[ComposerView]]:
        ids = list(song_ids)
        if not ids:
            return {}
        stmt = (
            select(SongComposerLink.song_id, ComposerModel.id, ComposerModel.name)
            .join(ComposerModel, ComposerModel.id == SongComposerLink.composer_id)
            .where(SongComposerLink.song_id.in_(ids))
            .order_by(ComposerModel.name)
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[UUID, list[ComposerView]] = defaultdict(list)
        for song_id, c_id, c_name in rows:
            result[song_id].append(ComposerView(id=c_id, name=c_name))
        return result

    async def _fetch_taxonomies_by_songs(
        self, song_ids: Iterable[UUID]
    ) -> dict[UUID, list[TaxonomyValueView]]:
        ids = list(song_ids)
        if not ids:
            return {}
        stmt = (
            select(SongTaxonomyValueLink.song_id, TaxonomyValueModel)
            .join(
                TaxonomyValueModel,
                TaxonomyValueModel.id == SongTaxonomyValueLink.taxonomy_value_id,
            )
            .where(SongTaxonomyValueLink.song_id.in_(ids))
            .order_by(TaxonomyValueModel.name)
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[UUID, list[TaxonomyValueView]] = defaultdict(list)
        for song_id, tv in rows:
            result[song_id].append(
                TaxonomyValueView(
                    id=tv.id,
                    kind=tv.kind,
                    name=tv.name,
                    version=tv.version,
                    created_at=tv.created_at,
                    updated_at=tv.updated_at,
                )
            )
        return result


def _split_taxonomies_by_kind(
    values: Iterable[TaxonomyValueView],
) -> tuple[list[TaxonomyValueView], list[TaxonomyValueView], list[TaxonomyValueView]]:
    seasons: list[TaxonomyValueView] = []
    masses: list[TaxonomyValueView] = []
    special: list[TaxonomyValueView] = []
    for v in values:
        if v.kind == TaxonomyKind.SEASON.value:
            seasons.append(v)
        elif v.kind == TaxonomyKind.MASS.value:
            masses.append(v)
        elif v.kind == TaxonomyKind.SPECIAL_EVENT.value:
            special.append(v)
    return seasons, masses, special
