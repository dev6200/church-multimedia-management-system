"""Contract test for ``DELETE /api/v1/songs/{id}`` (T088).

Covers FR-012, FR-030:
- 204 on success
- 409 on version mismatch
- 403 for USER role
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
async def test_delete_song_returns_204(client, seeded_admin) -> None:
    song = await _create(client)
    response = await client.delete(
        f"/api/v1/songs/{song['id']}",
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(song["version"]),
        },
    )
    assert response.status_code == 204


@pytest.mark.contract
async def test_delete_song_stale_version_returns_409(client, seeded_admin) -> None:
    song = await _create(client)
    response = await client.delete(
        f"/api/v1/songs/{song['id']}",
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(song["version"] + 7),
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict_version"


@pytest.mark.contract
async def test_delete_song_user_role_returns_403(
    client, seeded_admin, seeded_user
) -> None:
    song = await _create(client)
    response = await client.delete(
        f"/api/v1/songs/{song['id']}",
        headers={
            "Authorization": "Bearer user-token",
            "If-Match": str(song["version"]),
        },
    )
    assert response.status_code == 403
