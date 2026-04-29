"""Unit test for ``ListSongs`` (T053).

Covers FR-022/023/024 invariants at the application layer:
- ``q`` matches title and composer name
- multi-taxonomy filter ANDs across kinds, ORs within a kind
- pagination math (page/page_size produce correct slice and total)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.list_songs import ListSongs
from src.domain.entities import Composer, Song, SongOptionalLink
from src.domain.repositories import Pagination, SongFilters
from src.domain.value_objects import LinkUrl, TaxonomyKind
from tests.unit.fakes import InMemoryUnitOfWork


def _composer(name: str) -> Composer:
    return Composer(
        id=uuid4(),
        name=name,
        name_norm=name.lower().strip(),
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )


def _make_song(
    *,
    title: str,
    composers: list[Composer],
    taxonomy_value_ids: set[UUID] | None = None,
    optional_links: tuple[SongOptionalLink, ...] = (),
    actor_id: UUID | None = None,
    when: datetime | None = None,
) -> Song:
    return Song.create(
        id=uuid4(),
        title=title,
        composers=composers,
        taxonomy_value_ids=frozenset(taxonomy_value_ids or set()),
        optional_links=optional_links,
        actor_id=actor_id or uuid4(),
        now=when or datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


async def test_list_songs_q_matches_title(uow: InMemoryUnitOfWork) -> None:
    s1 = _make_song(title="Salve Regina", composers=[_composer("Anonymous")])
    s2 = _make_song(title="Ave Maria", composers=[_composer("Schubert")])
    await uow.songs.add(s1, composers=[])
    await uow.songs.add(s2, composers=[])

    use_case = ListSongs(uow=uow)
    result = await use_case.execute(
        filters=SongFilters(q="salve"), pagination=Pagination(page=1, page_size=20)
    )
    assert {s.id for s in result.items} == {s1.id}


async def test_list_songs_q_matches_composer_name(uow: InMemoryUnitOfWork) -> None:
    s1 = _make_song(title="Salve Regina", composers=[_composer("Palestrina")])
    s2 = _make_song(title="Ave Maria", composers=[_composer("Schubert")])
    await uow.songs.add(s1, composers=[])
    await uow.songs.add(s2, composers=[])

    use_case = ListSongs(uow=uow)
    result = await use_case.execute(
        filters=SongFilters(q="schubert"), pagination=Pagination(page=1, page_size=20)
    )
    assert {s.id for s in result.items} == {s2.id}


async def test_list_songs_taxonomy_filter_or_within_kind(
    uow: InMemoryUnitOfWork,
) -> None:
    season_a = uuid4()
    season_b = uuid4()
    s1 = _make_song(
        title="Advent Hymn",
        composers=[_composer("X")],
        taxonomy_value_ids={season_a},
    )
    s2 = _make_song(
        title="Christmas Hymn",
        composers=[_composer("Y")],
        taxonomy_value_ids={season_b},
    )
    s3 = _make_song(title="Random", composers=[_composer("Z")])
    for s in (s1, s2, s3):
        await uow.songs.add(s, composers=[])

    use_case = ListSongs(uow=uow)
    result = await use_case.execute(
        filters=SongFilters(
            taxonomy_value_ids_by_kind={
                TaxonomyKind.SEASON: frozenset({season_a, season_b}),
            }
        ),
        pagination=Pagination(page=1, page_size=20),
    )
    assert {s.id for s in result.items} == {s1.id, s2.id}


async def test_list_songs_taxonomy_filter_and_across_kinds(
    uow: InMemoryUnitOfWork,
) -> None:
    season_advent = uuid4()
    mass_first_sunday = uuid4()
    s_both = _make_song(
        title="Eligible",
        composers=[_composer("X")],
        taxonomy_value_ids={season_advent, mass_first_sunday},
    )
    s_only_season = _make_song(
        title="Only Season",
        composers=[_composer("Y")],
        taxonomy_value_ids={season_advent},
    )
    s_only_mass = _make_song(
        title="Only Mass",
        composers=[_composer("Z")],
        taxonomy_value_ids={mass_first_sunday},
    )
    for s in (s_both, s_only_season, s_only_mass):
        await uow.songs.add(s, composers=[])

    use_case = ListSongs(uow=uow)
    result = await use_case.execute(
        filters=SongFilters(
            taxonomy_value_ids_by_kind={
                TaxonomyKind.SEASON: frozenset({season_advent}),
                TaxonomyKind.MASS: frozenset({mass_first_sunday}),
            }
        ),
        pagination=Pagination(page=1, page_size=20),
    )
    assert {s.id for s in result.items} == {s_both.id}


async def test_list_songs_pagination_math(uow: InMemoryUnitOfWork) -> None:
    base = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(25):
        s = _make_song(
            title=f"Song {i:02d}",
            composers=[_composer("Composer")],
            when=base.replace(minute=i),  # newer i → newer updated_at
        )
        await uow.songs.add(s, composers=[])

    use_case = ListSongs(uow=uow)
    page1 = await use_case.execute(
        filters=SongFilters(), pagination=Pagination(page=1, page_size=10)
    )
    page3 = await use_case.execute(
        filters=SongFilters(), pagination=Pagination(page=3, page_size=10)
    )
    assert page1.total == 25
    assert len(page1.items) == 10
    assert page3.total == 25
    assert len(page3.items) == 5
    # Ordering: page1's first item is the newest
    assert page1.items[0].title == "Song 24"


async def test_list_songs_empty_result(uow: InMemoryUnitOfWork) -> None:
    use_case = ListSongs(uow=uow)
    result = await use_case.execute(
        filters=SongFilters(q="nothing here"),
        pagination=Pagination(page=1, page_size=20),
    )
    assert result.items == []
    assert result.total == 0
