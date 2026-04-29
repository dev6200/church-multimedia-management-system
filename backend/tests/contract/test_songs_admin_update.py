"""Contract test for ``PUT /api/v1/songs/{id}`` (T087).

Covers FR-011, FR-030:
- If-Match required → 428 when missing
- 409 conflict_version on mismatch
- 200 on happy path with version incremented
"""

from __future__ import annotations

import pytest


async def _create(client) -> dict:
    res = await client.post(
        "/api/v1/admin/songs",
        json={"title": "Salve Regina", "composers": [{"name": "Anonymous"}]},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.contract
async def test_update_song_happy_path_increments_version(
    client, seeded_admin
) -> None:
    song = await _create(client)
    response = await client.put(
        f"/api/v1/songs/{song['id']}",
        json={"title": "Salve Regina, Mater", "composers": [{"name": "Anonymous"}]},
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(song["version"]),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Salve Regina, Mater"
    assert body["version"] == song["version"] + 1


@pytest.mark.contract
async def test_update_song_missing_if_match_returns_428(
    client, seeded_admin
) -> None:
    song = await _create(client)
    response = await client.put(
        f"/api/v1/songs/{song['id']}",
        json={"title": "Renamed", "composers": [{"name": "Anonymous"}]},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 428
    assert response.json()["detail"]["code"] == "if_match_required"


@pytest.mark.contract
async def test_update_song_stale_version_returns_409_conflict_version(
    client, seeded_admin
) -> None:
    song = await _create(client)
    response = await client.put(
        f"/api/v1/songs/{song['id']}",
        json={"title": "Renamed", "composers": [{"name": "Anonymous"}]},
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(song["version"] + 99),
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict_version"
