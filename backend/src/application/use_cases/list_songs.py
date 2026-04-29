"""ListSongs use case (T066) — public, paginated catalog browse (FR-022..FR-024)."""

from __future__ import annotations

from src.application.ports import UnitOfWork
from src.domain.queries.song_views import SongSummaryPage
from src.domain.repositories import Pagination, SongFilters

__all__ = ["ListSongs"]


class ListSongs:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, filters: SongFilters, pagination: Pagination
    ) -> SongSummaryPage:
        async with self._uow:
            return await self._uow.songs.search_summary_views(filters, pagination)
