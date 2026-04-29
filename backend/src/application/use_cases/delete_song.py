"""DeleteSong use case (T095) — FR-012, FR-030."""

from __future__ import annotations

from uuid import UUID

from src.application.ports import UnitOfWork

__all__ = ["DeleteSong"]


class DeleteSong:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, song_id: UUID, *, expected_version: int) -> None:
        async with self._uow:
            await self._uow.songs.delete_with_version(
                song_id, expected_version=expected_version
            )
            await self._uow.commit()
