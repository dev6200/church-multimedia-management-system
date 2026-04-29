"""Unit test for ``UpdateSong`` (T082)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.create_song import (
    CreateSong,
    CreateSongInput,
)
from src.application.use_cases.update_song import UpdateSong, UpdateSongInput
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateSongError, VersionConflictError
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


async def _seed_song(uow: InMemoryUnitOfWork, *, title: str, composer: str):
    return await CreateSong(uow=uow, clock=FixedClock()).execute(
        CreateSongInput(
            title=title,
            composer_names=(composer,),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=_actor(),
    )


async def test_update_song_increments_version(uow: InMemoryUnitOfWork) -> None:
    seed = await _seed_song(uow, title="Salve Regina", composer="Anonymous")
    use_case = UpdateSong(uow=uow, clock=FixedClock())
    updated = await use_case.execute(
        seed.id,
        UpdateSongInput(
            title="Salve Regina, Mater",
            composer_names=("Anonymous",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
            expected_version=seed.version,
        ),
        actor=_actor(),
    )
    assert updated.version == seed.version + 1
    assert updated.title == "Salve Regina, Mater"


async def test_update_song_with_stale_version_raises(
    uow: InMemoryUnitOfWork,
) -> None:
    seed = await _seed_song(uow, title="Salve Regina", composer="Anonymous")
    use_case = UpdateSong(uow=uow, clock=FixedClock())
    with pytest.raises(VersionConflictError):
        await use_case.execute(
            seed.id,
            UpdateSongInput(
                title="Salve Regina, Mater",
                composer_names=("Anonymous",),
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(),
                expected_version=seed.version + 99,
            ),
            actor=_actor(),
        )


async def test_update_song_rename_into_existing_dedup_key_raises(
    uow: InMemoryUnitOfWork,
) -> None:
    a = await _seed_song(uow, title="Ave Maria", composer="Schubert")
    b = await _seed_song(uow, title="Ave Verum", composer="Schubert")

    use_case = UpdateSong(uow=uow, clock=FixedClock())
    with pytest.raises(DuplicateSongError) as exc:
        await use_case.execute(
            b.id,
            UpdateSongInput(
                title="Ave Maria",  # collides with `a`
                composer_names=("Schubert",),
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(),
                expected_version=b.version,
            ),
            actor=_actor(),
        )
    assert exc.value.conflicting_song_id == a.id


async def test_update_song_rename_to_same_dedup_key_succeeds(
    uow: InMemoryUnitOfWork,
) -> None:
    seed = await _seed_song(uow, title="Ave Maria", composer="Schubert")
    use_case = UpdateSong(uow=uow, clock=FixedClock())
    # Same dedup key but different display ("Ave maria" -> "ave maria") works.
    updated = await use_case.execute(
        seed.id,
        UpdateSongInput(
            title="Ave maria",
            composer_names=("Schubert",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
            expected_version=seed.version,
        ),
        actor=_actor(),
    )
    assert updated.title == "Ave maria"
