"""Unit test for ``GetSong`` (T054)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.get_song import GetSong
from src.domain.entities import Composer, Song
from src.domain.errors import NotFoundError
from tests.unit.fakes import InMemoryUnitOfWork


def _composer(name: str) -> Composer:
    return Composer(
        id=uuid4(),
        name=name,
        name_norm=name.lower(),
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


async def test_get_song_returns_existing_song(uow: InMemoryUnitOfWork) -> None:
    song = Song.create(
        id=uuid4(),
        title="Salve Regina",
        composers=[_composer("Anonymous")],
        taxonomy_value_ids=frozenset(),
        optional_links=(),
        actor_id=uuid4(),
        now=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    await uow.songs.add(song, composers=[])

    fetched = await GetSong(uow=uow).execute(song.id)
    assert fetched.id == song.id


async def test_get_song_raises_not_found_for_unknown_id(
    uow: InMemoryUnitOfWork,
) -> None:
    with pytest.raises(NotFoundError):
        await GetSong(uow=uow).execute(uuid4())
