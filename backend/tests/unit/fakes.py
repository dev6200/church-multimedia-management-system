"""Shared in-memory repository fakes for unit tests.

These fakes implement the domain repository ABCs so use-case unit tests can
execute without I/O. They are intentionally simple — no FK enforcement, no
trigram parity. Integration tests cover the SQL semantics.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from types import TracebackType
from uuid import UUID

from src.application.ports import Clock, UnitOfWork
from src.domain.entities import (
    Composer,
    OptionalFieldDefinition,
    Song,
    TaxonomyValue,
    UserAccount,
)
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
    OptionalFieldRepository,
    Pagination,
    SongFilters,
    SongPage,
    SongRepository,
    TaxonomyRepository,
    UserPage,
    UserRepository,
)
from src.domain.value_objects import DedupKey, Role, TaxonomyKind


class FixedClock(Clock):
    def __init__(self, instant: datetime | None = None) -> None:
        self._instant = instant or datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._instant


class InMemorySongRepository(SongRepository):
    def __init__(
        self,
        *,
        taxonomies: "InMemoryTaxonomyRepository | None" = None,
        optional_fields: "InMemoryOptionalFieldRepository | None" = None,
    ) -> None:
        self.store: dict[UUID, Song] = {}
        self.composers: dict[UUID, Composer] = {}
        # Per-song optional-field values: song_id -> {definition_id: value_url}
        self.optional_links: dict[UUID, dict[UUID, str]] = {}
        # Back-references to the sibling repos so the read views can resolve
        # taxonomy and optional-field labels. Wired by ``InMemoryUnitOfWork``.
        self._taxonomies = taxonomies
        self._optional_fields = optional_fields

    async def get_by_id(self, song_id: UUID) -> Song | None:
        # Return a copy so the use case mutating the entity in-place doesn't
        # alias the row in the store (the production SQL repo reconstructs a
        # fresh entity from a row, so the store-side row stays at the old
        # version until update_with_version commits).
        existing = self.store.get(song_id)
        return copy.deepcopy(existing) if existing else None

    async def find_by_dedup_key(self, dedup_key: DedupKey) -> Song | None:
        for s in self.store.values():
            if s.dedup_key == dedup_key:
                return copy.deepcopy(s)
        return None

    async def find_composer_by_norm(self, name_norm: str):
        for c in self.composers.values():
            if c.name_norm == name_norm:
                return copy.deepcopy(c)
        return None

    async def search(
        self, filters: SongFilters, pagination: Pagination
    ) -> SongPage:
        items = list(self.store.values())
        if filters.q:
            ql = filters.q.lower()
            items = [
                s
                for s in items
                if ql in s.title.lower()
                or any(ql in name.lower() for name in s.composer_names)
            ]
        for kind, ids in filters.taxonomy_value_ids_by_kind.items():
            if not ids:
                continue
            items = [s for s in items if any(i in s.taxonomy_value_ids for i in ids)]
        items.sort(key=lambda s: s.updated_at, reverse=True)
        total = len(items)
        start = pagination.offset()
        page_items = items[start : start + pagination.page_size]
        return SongPage(
            items=page_items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def add(self, song: Song, *, composers: list[Composer]) -> None:
        if any(s.dedup_key == song.dedup_key for s in self.store.values()):
            existing = next(s for s in self.store.values() if s.dedup_key == song.dedup_key)
            raise DuplicateSongError(
                "Duplicate (title, composer set)",
                conflicting_song_id=existing.id,
            )
        for c in composers:
            self.composers[c.id] = c
        self.store[song.id] = song

    async def update_with_version(
        self, song: Song, *, composers: list[Composer], expected_version: int
    ) -> None:
        existing = self.store.get(song.id)
        if existing is None:
            raise VersionConflictError(expected_version=expected_version)
        if existing.version != expected_version:
            raise VersionConflictError(expected_version=expected_version)
        # Detect dedup conflict against OTHER songs.
        for other in self.store.values():
            if other.id != song.id and other.dedup_key == song.dedup_key:
                raise DuplicateSongError(
                    "Duplicate (title, composer set)",
                    conflicting_song_id=other.id,
                )
        for c in composers:
            self.composers[c.id] = c
        self.store[song.id] = song

    async def delete_with_version(
        self, song_id: UUID, *, expected_version: int
    ) -> None:
        existing = self.store.get(song_id)
        if existing is None or existing.version != expected_version:
            raise VersionConflictError(expected_version=expected_version)
        del self.store[song_id]

    # ---------------------------------------------------------- read views
    async def search_summary_views(
        self, filters: SongFilters, pagination: Pagination
    ) -> SongSummaryPage:
        items = list(self.store.values())
        if filters.q:
            ql = filters.q.lower()
            items = [
                s
                for s in items
                if ql in s.title.lower()
                or any(ql in name.lower() for name in s.composer_names)
            ]
        for kind, ids in filters.taxonomy_value_ids_by_kind.items():
            if not ids:
                continue
            items = [s for s in items if any(i in s.taxonomy_value_ids for i in ids)]
        items.sort(key=lambda s: s.updated_at, reverse=True)
        total = len(items)
        start = pagination.offset()
        page_items = items[start : start + pagination.page_size]
        views: list[SongSummaryView] = []
        for s in page_items:
            seasons, masses, special = self._split_taxonomies(s.taxonomy_value_ids)
            views.append(
                SongSummaryView(
                    id=s.id,
                    title=s.title,
                    composers=tuple(self._composer_views_for_song(s)),
                    seasons=tuple(seasons),
                    masses=tuple(masses),
                    special_events=tuple(special),
                    version=s.version,
                )
            )
        return SongSummaryPage(
            items=views,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_detail_view(self, song_id: UUID) -> SongDetailView | None:
        s = self.store.get(song_id)
        if s is None:
            return None
        seasons, masses, special = self._split_taxonomies(s.taxonomy_value_ids)
        opt_views: list[OptionalFieldValueView] = []
        if self._optional_fields is not None:
            for def_id, url in (self.optional_links.get(s.id) or {}).items():
                definition = self._optional_fields.store.get(def_id)
                opt_views.append(
                    OptionalFieldValueView(
                        definition_id=def_id,
                        label=definition.label if definition else "",
                        value_url=url,
                    )
                )
        return SongDetailView(
            id=s.id,
            title=s.title,
            composers=tuple(self._composer_views_for_song(s)),
            seasons=tuple(seasons),
            masses=tuple(masses),
            special_events=tuple(special),
            optional_fields=tuple(opt_views),
            version=s.version,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )

    # ---------------------------------------------------------- helpers
    def _composer_views_for_song(self, song: Song) -> list[ComposerView]:
        out: list[ComposerView] = []
        for cid, name in zip(song.composer_ids, song.composer_names, strict=False):
            composer = self.composers.get(cid)
            display = composer.name if composer else name
            out.append(ComposerView(id=cid, name=display))
        # Stable order by composer name for tests.
        out.sort(key=lambda c: c.name.lower())
        return out

    def _split_taxonomies(
        self, value_ids: frozenset[UUID]
    ) -> tuple[
        list[TaxonomyValueView], list[TaxonomyValueView], list[TaxonomyValueView]
    ]:
        seasons: list[TaxonomyValueView] = []
        masses: list[TaxonomyValueView] = []
        special: list[TaxonomyValueView] = []
        if self._taxonomies is None:
            return seasons, masses, special
        for vid in value_ids:
            tv = self._taxonomies.store.get(vid)
            if tv is None:
                continue
            view = TaxonomyValueView(
                id=tv.id,
                kind=tv.kind.value,
                name=tv.name,
                version=tv.version,
                created_at=tv.created_at,
                updated_at=tv.updated_at,
            )
            if tv.kind is TaxonomyKind.SEASON:
                seasons.append(view)
            elif tv.kind is TaxonomyKind.MASS:
                masses.append(view)
            elif tv.kind is TaxonomyKind.SPECIAL_EVENT:
                special.append(view)
        for arr in (seasons, masses, special):
            arr.sort(key=lambda v: v.name.lower())
        return seasons, masses, special


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.store: dict[UUID, UserAccount] = {}

    async def get_by_id(self, user_id: UUID) -> UserAccount | None:
        existing = self.store.get(user_id)
        return copy.deepcopy(existing) if existing else None

    async def get_by_clerk_id(self, clerk_user_id: str) -> UserAccount | None:
        for u in self.store.values():
            if u.clerk_user_id == clerk_user_id:
                return copy.deepcopy(u)
        return None

    async def add(self, user: UserAccount) -> None:
        self.store[user.id] = user

    async def list_paginated(
        self, *, page: int, page_size: int, q: str | None = None
    ) -> UserPage:
        items = list(self.store.values())
        if q:
            ql = q.lower()
            items = [
                u
                for u in items
                if ql in u.email.lower() or ql in (u.display_name or "").lower()
            ]
        items.sort(key=lambda u: u.email)
        total = len(items)
        start = (page - 1) * page_size
        return UserPage(
            items=items[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def count_by_role(self, role: Role) -> int:
        return sum(1 for u in self.store.values() if u.role is role)

    async def update_role_with_version(
        self, user: UserAccount, *, expected_version: int
    ) -> None:
        existing = self.store.get(user.id)
        if existing is None or existing.version != expected_version:
            raise VersionConflictError(expected_version=expected_version)
        self.store[user.id] = user


class InMemoryTaxonomyRepository(TaxonomyRepository):
    def __init__(self) -> None:
        self.store: dict[UUID, TaxonomyValue] = {}
        self.usage: dict[UUID, int] = {}

    async def get_by_id(self, value_id: UUID) -> TaxonomyValue | None:
        existing = self.store.get(value_id)
        return copy.deepcopy(existing) if existing else None

    async def list_by_kind(self, kind: TaxonomyKind) -> list[TaxonomyValue]:
        return sorted(
            (v for v in self.store.values() if v.kind is kind),
            key=lambda v: v.name.lower(),
        )

    async def find_by_kind_and_norm(
        self, kind: TaxonomyKind, name_norm: str
    ) -> TaxonomyValue | None:
        for v in self.store.values():
            if v.kind is kind and v.name_norm == name_norm:
                return v
        return None

    async def add(self, value: TaxonomyValue) -> None:
        self.store[value.id] = value

    async def rename_with_version(
        self, value: TaxonomyValue, *, expected_version: int
    ) -> None:
        existing = self.store.get(value.id)
        if existing is None or existing.version != expected_version:
            raise VersionConflictError(expected_version=expected_version)
        self.store[value.id] = value

    async def count_usage(self, value_id: UUID) -> int:
        return self.usage.get(value_id, 0)

    async def delete_with_detach(self, value_id: UUID, *, detach: bool) -> int:
        usage_count = self.usage.pop(value_id, 0)
        if usage_count > 0 and not detach:
            from src.domain.errors import TaxonomyInUseError

            raise TaxonomyInUseError(
                f"Value in use by {usage_count} song(s)", usage_count=usage_count
            )
        self.store.pop(value_id, None)
        return usage_count


class InMemoryOptionalFieldRepository(OptionalFieldRepository):
    def __init__(self) -> None:
        self.store: dict[UUID, OptionalFieldDefinition] = {}
        self.usage: dict[UUID, int] = {}

    async def get_by_id(self, definition_id: UUID) -> OptionalFieldDefinition | None:
        existing = self.store.get(definition_id)
        return copy.deepcopy(existing) if existing else None

    async def list_all(self) -> list[OptionalFieldDefinition]:
        return sorted(self.store.values(), key=lambda d: d.label.lower())

    async def find_by_norm(self, label_norm: str) -> OptionalFieldDefinition | None:
        for d in self.store.values():
            if d.label_norm == label_norm:
                return d
        return None

    async def add(self, definition: OptionalFieldDefinition) -> None:
        self.store[definition.id] = definition

    async def rename_with_version(
        self, definition: OptionalFieldDefinition, *, expected_version: int
    ) -> None:
        existing = self.store.get(definition.id)
        if existing is None or existing.version != expected_version:
            raise VersionConflictError(expected_version=expected_version)
        self.store[definition.id] = definition

    async def count_usage(self, definition_id: UUID) -> int:
        return self.usage.get(definition_id, 0)

    async def delete_with_detach(self, definition_id: UUID, *, detach: bool) -> int:
        usage_count = self.usage.pop(definition_id, 0)
        if usage_count > 0 and not detach:
            from src.domain.errors import TaxonomyInUseError

            raise TaxonomyInUseError(
                f"Definition in use by {usage_count} song(s)", usage_count=usage_count
            )
        self.store.pop(definition_id, None)
        return usage_count


class InMemoryUnitOfWork(UnitOfWork):
    # Narrow the abstract repo types so tests can read `uow.users.store` etc.
    # without pyright flagging unknown attributes on the ABCs.
    songs: "InMemorySongRepository"
    users: "InMemoryUserRepository"
    taxonomies: "InMemoryTaxonomyRepository"
    optional_fields: "InMemoryOptionalFieldRepository"

    def __init__(self) -> None:
        self.taxonomies = InMemoryTaxonomyRepository()
        self.optional_fields = InMemoryOptionalFieldRepository()
        self.songs = InMemorySongRepository(
            taxonomies=self.taxonomies,
            optional_fields=self.optional_fields,
        )
        self.users = InMemoryUserRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
