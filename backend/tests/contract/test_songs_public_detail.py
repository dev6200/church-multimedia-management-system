"""Contract test for ``GET /api/v1/songs/{id}`` (T057).

Asserts FR-025, FR-031:
- anonymous can fetch detail (200)
- unknown id → 404 with ``not_found`` code
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.entities import Composer, Song


def _composer(name: str) -> Composer:
    return Composer(
        id=uuid4(),
        name=name,
        name_norm=name.lower(),
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )


@pytest.mark.contract
async def test_get_existing_song_returns_detail(
    client, songs_store
) -> None:
    song = Song.create(
        id=uuid4(),
        title="Salve Regina",
        composers=[_composer("Anonymous")],
        taxonomy_value_ids=frozenset(),
        optional_links=(),
        actor_id=uuid4(),
        now=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    songs_store[song.id] = song

    response = await client.get(f"/api/v1/songs/{song.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(song.id)
    assert body["title"] == "Salve Regina"
    assert {"composers", "seasons", "masses", "special_events", "optional_fields", "created_at", "updated_at", "version"} <= body.keys()


@pytest.mark.contract
async def test_unknown_id_returns_404_with_not_found_code(client) -> None:
    response = await client.get(f"/api/v1/songs/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
