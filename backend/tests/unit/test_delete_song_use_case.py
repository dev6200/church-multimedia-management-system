"""Unit test for ``DeleteSong`` (T083)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.create_song import CreateSong, CreateSongInput
from src.application.use_cases.delete_song import DeleteSong
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import VersionConflictError
from src.domain.value_objects import Role
from tests.unit.fakes import FixedClock, InMemoryUnitOfWork


def _actor() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        clerk_user_id="admin",
        email="admin@parish.example.org",
        role=Role.ADMIN,
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


async def test_delete_song_removes_from_store(uow: InMemoryUnitOfWork) -> None:
    seed = await CreateSong(uow=uow, clock=FixedClock()).execute(
        CreateSongInput(
            title="Salve Regina",
            composer_names=("Anonymous",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=_actor(),
    )
    await DeleteSong(uow=uow).execute(seed.id, expected_version=seed.version)
    assert seed.id not in uow.songs.store


async def test_delete_song_version_mismatch_raises(uow: InMemoryUnitOfWork) -> None:
    seed = await CreateSong(uow=uow, clock=FixedClock()).execute(
        CreateSongInput(
            title="Salve Regina",
            composer_names=("Anonymous",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=_actor(),
    )
    with pytest.raises(VersionConflictError):
        await DeleteSong(uow=uow).execute(seed.id, expected_version=seed.version + 99)
