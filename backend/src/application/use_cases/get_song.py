"""GetSong use case (T067) — public song-detail fetch (FR-025)."""

from __future__ import annotations

from uuid import UUID

from src.application.ports import UnitOfWork
from src.domain.errors import NotFoundError
from src.domain.queries.song_views import SongDetailView

__all__ = ["GetSong"]


class GetSong:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, song_id: UUID) -> SongDetailView:
        async with self._uow:
            view = await self._uow.songs.get_detail_view(song_id)
        if view is None:
            raise NotFoundError("Song not found", song_id=str(song_id))
        return view
