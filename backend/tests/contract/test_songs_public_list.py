"""Contract test for ``GET /api/v1/songs`` (T056).

Asserts FR-022 / FR-023 / FR-024 / FR-031:
- anonymous access permitted (200)
- ``q`` matches title and composer
- repeated ``season=...&season=...`` ORs within a kind
- ``season=...&mass=...`` ANDs across kinds
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.domain.entities import Composer, Song, TaxonomyValue
from src.domain.value_objects import TaxonomyKind


def _composer(name: str) -> Composer:
    return Composer(
        id=uuid4(),
        name=name,
        name_norm=name.lower(),
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )


def _seed_song(
    *,
    songs_store,
    title: str,
    composers: list[Composer],
    taxonomy_value_ids: set[UUID] | None = None,
    when: datetime | None = None,
) -> Song:
    song = Song.create(
        id=uuid4(),
        title=title,
        composers=composers,
        taxonomy_value_ids=frozenset(taxonomy_value_ids or set()),
        optional_links=(),
        actor_id=uuid4(),
        now=when or datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    songs_store[song.id] = song
    return song


def _seed_taxonomy(
    *,
    taxonomies_store,
    kind: TaxonomyKind,
    name: str,
) -> TaxonomyValue:
    actor = uuid4()
    tv = TaxonomyValue.create(
        id=uuid4(),
        kind=kind,
        name=name,
        actor_id=actor,
        now=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    taxonomies_store[tv.id] = tv
    return tv


@pytest.mark.contract
async def test_anonymous_can_list_songs(
    client, songs_store
) -> None:
    _seed_song(songs_store=songs_store, title="Salve Regina", composers=[_composer("Anonymous")])

    response = await client.get("/api/v1/songs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Salve Regina"
    assert {"id", "title", "composers", "seasons", "masses", "special_events", "version"} <= body["items"][0].keys()


@pytest.mark.contract
async def test_q_matches_title_and_composer(client, songs_store) -> None:
    _seed_song(songs_store=songs_store, title="Salve Regina", composers=[_composer("Palestrina")])
    _seed_song(songs_store=songs_store, title="Ave Maria", composers=[_composer("Schubert")])

    by_title = await client.get("/api/v1/songs", params={"q": "salve"})
    assert by_title.status_code == 200
    titles = [s["title"] for s in by_title.json()["items"]]
    assert titles == ["Salve Regina"]

    by_composer = await client.get("/api/v1/songs", params={"q": "schubert"})
    assert by_composer.status_code == 200
    titles = [s["title"] for s in by_composer.json()["items"]]
    assert titles == ["Ave Maria"]


@pytest.mark.contract
async def test_taxonomy_filter_or_within_kind(
    client, songs_store, taxonomies_store
) -> None:
    advent = _seed_taxonomy(taxonomies_store=taxonomies_store, kind=TaxonomyKind.SEASON, name="Advent")
    christmas = _seed_taxonomy(taxonomies_store=taxonomies_store, kind=TaxonomyKind.SEASON, name="Christmas")
    _seed_song(songs_store=songs_store, title="A", composers=[_composer("X")], taxonomy_value_ids={advent.id})
    _seed_song(songs_store=songs_store, title="B", composers=[_composer("Y")], taxonomy_value_ids={christmas.id})
    _seed_song(songs_store=songs_store, title="C", composers=[_composer("Z")])

    response = await client.get(
        "/api/v1/songs",
        params={"season": [str(advent.id), str(christmas.id)]},
    )
    assert response.status_code == 200
    titles = sorted(s["title"] for s in response.json()["items"])
    assert titles == ["A", "B"]


@pytest.mark.contract
async def test_taxonomy_filter_and_across_kinds(
    client, songs_store, taxonomies_store
) -> None:
    advent = _seed_taxonomy(taxonomies_store=taxonomies_store, kind=TaxonomyKind.SEASON, name="Advent")
    first_sunday = _seed_taxonomy(
        taxonomies_store=taxonomies_store,
        kind=TaxonomyKind.MASS,
        name="1st Sunday of Advent",
    )
    _seed_song(
        songs_store=songs_store,
        title="Both",
        composers=[_composer("X")],
        taxonomy_value_ids={advent.id, first_sunday.id},
    )
    _seed_song(
        songs_store=songs_store,
        title="OnlySeason",
        composers=[_composer("Y")],
        taxonomy_value_ids={advent.id},
    )

    response = await client.get(
        "/api/v1/songs",
        params={"season": [str(advent.id)], "mass": [str(first_sunday.id)]},
    )
    assert response.status_code == 200
    titles = [s["title"] for s in response.json()["items"]]
    assert titles == ["Both"]
