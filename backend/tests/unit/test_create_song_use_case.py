"""Unit test for ``CreateSong`` (T081)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.create_song import (
    CreateSong,
    CreateSongInput,
    OptionalLinkInput,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateSongError
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


async def test_create_song_persists_with_required_fields(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    use_case = CreateSong(uow=uow, clock=FixedClock())
    song = await use_case.execute(
        CreateSongInput(
            title="Salve Regina",
            composer_names=("Anonymous",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=actor,
    )
    assert song.title == "Salve Regina"
    assert song.created_by == actor.id
    assert song.updated_by == actor.id
    assert uow.songs.store[song.id] is song
    assert uow.committed is True


async def test_create_song_rejects_empty_title(uow: InMemoryUnitOfWork) -> None:
    use_case = CreateSong(uow=uow, clock=FixedClock())
    with pytest.raises(ValueError):
        await use_case.execute(
            CreateSongInput(
                title="   ",
                composer_names=("Anonymous",),
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(),
            ),
            actor=_actor(),
        )


async def test_create_song_rejects_empty_composer_list(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateSong(uow=uow, clock=FixedClock())
    with pytest.raises(ValueError):
        await use_case.execute(
            CreateSongInput(
                title="Salve Regina",
                composer_names=(),
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(),
            ),
            actor=_actor(),
        )


async def test_create_song_rejects_duplicate_title_and_composer_set(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateSong(uow=uow, clock=FixedClock())
    actor = _actor()
    first = await use_case.execute(
        CreateSongInput(
            title="Ave Maria",
            composer_names=("Schubert",),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=actor,
    )

    with pytest.raises(DuplicateSongError) as exc_info:
        await use_case.execute(
            CreateSongInput(
                title="ave maria",  # different case
                composer_names=("schubert",),  # different case
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(),
            ),
            actor=actor,
        )
    assert exc_info.value.conflicting_song_id == first.id


async def test_create_song_rejects_invalid_optional_link_url(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateSong(uow=uow, clock=FixedClock())
    with pytest.raises(ValueError):
        await use_case.execute(
            CreateSongInput(
                title="Salve Regina",
                composer_names=("Anonymous",),
                season_ids=frozenset(),
                mass_ids=frozenset(),
                special_event_ids=frozenset(),
                optional_links=(
                    OptionalLinkInput(
                        definition_id=uuid4(),
                        value_url="javascript:alert(1)",
                    ),
                ),
            ),
            actor=_actor(),
        )


async def test_create_song_dedups_composers_in_input(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateSong(uow=uow, clock=FixedClock())
    song = await use_case.execute(
        CreateSongInput(
            title="Test",
            composer_names=("J.S. Bach", "j.s. bach", "  J.S. BACH  "),
            season_ids=frozenset(),
            mass_ids=frozenset(),
            special_event_ids=frozenset(),
            optional_links=(),
        ),
        actor=_actor(),
    )
    assert len(song.composer_ids) == 1
