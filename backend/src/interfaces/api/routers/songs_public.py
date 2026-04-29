"""Public-readable songs endpoints — FR-022, FR-023, FR-024, FR-025, FR-031.

Anonymous access permitted; no Bearer token required (FR-031). Mutating
endpoints live in ``songs_admin.py`` (Phase 4).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from src.application.ports import UnitOfWork
from src.application.use_cases.get_song import GetSong
from src.application.use_cases.list_songs import ListSongs
from src.domain.queries.song_views import (
    ComposerView,
    OptionalFieldValueView,
    SongDetailView,
    SongSummaryPage,
    SongSummaryView,
    TaxonomyValueView,
)
from src.domain.repositories import Pagination, SongFilters
from src.domain.value_objects import TaxonomyKind
from src.interfaces.api.deps import get_uow
from src.interfaces.api.schemas.common import (
    ComposerSchema,
    OptionalFieldValueSchema,
    TaxonomyValueSchema,
)
from src.interfaces.api.schemas.songs import (
    SongDetailSchema,
    SongPageSchema,
    SongSummarySchema,
)

router = APIRouter(prefix="/api/v1/songs", tags=["catalog"])


@router.get("", response_model=SongPageSchema)
async def list_songs(
    response: Response,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    season: Annotated[list[UUID] | None, Query()] = None,
    mass: Annotated[list[UUID] | None, Query()] = None,
    special_event: Annotated[list[UUID] | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SongPageSchema:
    filters = SongFilters(
        q=q,
        taxonomy_value_ids_by_kind={
            TaxonomyKind.SEASON: frozenset(season or []),
            TaxonomyKind.MASS: frozenset(mass or []),
            TaxonomyKind.SPECIAL_EVENT: frozenset(special_event or []),
        },
    )
    use_case = ListSongs(uow=uow)
    page_result: SongSummaryPage = await use_case.execute(
        filters=filters, pagination=Pagination(page=page, page_size=page_size)
    )
    response.headers["Cache-Control"] = "public, max-age=30, s-maxage=300"
    return SongPageSchema(
        items=[_summary_to_schema(item) for item in page_result.items],
        page=page_result.page,
        page_size=page_result.page_size,
        total=page_result.total,
    )


@router.get("/{song_id}", response_model=SongDetailSchema)
async def get_song(
    song_id: UUID,
    response: Response,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> SongDetailSchema:
    use_case = GetSong(uow=uow)
    detail: SongDetailView = await use_case.execute(song_id)
    response.headers["Cache-Control"] = "public, max-age=30, s-maxage=300"
    return _detail_to_schema(detail)


# ---------------------------------------------------------------- mappers
def _composer_to_schema(c: ComposerView) -> ComposerSchema:
    return ComposerSchema(id=c.id, name=c.name)


def _taxonomy_to_schema(t: TaxonomyValueView) -> TaxonomyValueSchema:
    return TaxonomyValueSchema(
        id=t.id,
        kind=t.kind,
        name=t.name,
        version=t.version,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _optional_to_schema(o: OptionalFieldValueView) -> OptionalFieldValueSchema:
    return OptionalFieldValueSchema(
        definition_id=o.definition_id,
        label=o.label,
        value_url=o.value_url,
    )


def _summary_to_schema(s: SongSummaryView) -> SongSummarySchema:
    return SongSummarySchema(
        id=s.id,
        title=s.title,
        composers=[_composer_to_schema(c) for c in s.composers],
        seasons=[_taxonomy_to_schema(t) for t in s.seasons],
        masses=[_taxonomy_to_schema(t) for t in s.masses],
        special_events=[_taxonomy_to_schema(t) for t in s.special_events],
        version=s.version,
    )


def _detail_to_schema(d: SongDetailView) -> SongDetailSchema:
    return SongDetailSchema(
        id=d.id,
        title=d.title,
        composers=[_composer_to_schema(c) for c in d.composers],
        seasons=[_taxonomy_to_schema(t) for t in d.seasons],
        masses=[_taxonomy_to_schema(t) for t in d.masses],
        special_events=[_taxonomy_to_schema(t) for t in d.special_events],
        optional_fields=[_optional_to_schema(o) for o in d.optional_fields],
        version=d.version,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )
