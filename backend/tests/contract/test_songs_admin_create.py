"""Contract test for ``POST /api/v1/admin/songs`` (T086).

Covers FR-008, FR-009, FR-004:
- 201 on minimum-payload (title + ≥1 composer)
- 401 anonymous
- 403 USER role
- 409 with conflicting_song_id on duplicate (title, composer set)
"""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_create_song_succeeds_with_minimum_payload(
    client, seeded_admin
) -> None:
    response = await client.post(
        "/api/v1/admin/songs",
        json={"title": "Salve Regina", "composers": [{"name": "Anonymous"}]},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Salve Regina"
    assert {"id", "composers", "version", "created_at", "updated_at"} <= body.keys()
    # Location header points at the public detail URL.
    location = response.headers.get("location")
    assert location is not None
    assert location.startswith("/api/v1/songs/")


@pytest.mark.contract
async def test_create_song_anonymous_returns_401(client) -> None:
    response = await client.post(
        "/api/v1/admin/songs",
        json={"title": "Salve Regina", "composers": [{"name": "Anonymous"}]},
    )
    assert response.status_code == 401


@pytest.mark.contract
async def test_create_song_user_role_returns_403(
    client, seeded_user
) -> None:
    response = await client.post(
        "/api/v1/admin/songs",
        json={"title": "Salve Regina", "composers": [{"name": "Anonymous"}]},
        headers={"Authorization": "Bearer user-token"},
    )
    assert response.status_code == 403


@pytest.mark.contract
async def test_create_song_missing_title_returns_400(
    client, seeded_admin
) -> None:
    response = await client.post(
        "/api/v1/admin/songs",
        json={"title": "   ", "composers": [{"name": "Anonymous"}]},
        headers={"Authorization": "Bearer admin-token"},
    )
    # 400 from validation — Pydantic min_length=1 OR domain rule via 422.
    assert response.status_code in (400, 422)


@pytest.mark.contract
async def test_create_song_duplicate_returns_409_with_conflicting_id(
    client, seeded_admin
) -> None:
    payload = {
        "title": "Ave Maria",
        "composers": [{"name": "Schubert"}],
    }
    first = await client.post(
        "/api/v1/admin/songs",
        json=payload,
        headers={"Authorization": "Bearer admin-token"},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    duplicate = await client.post(
        "/api/v1/admin/songs",
        json={"title": "ave maria", "composers": [{"name": "SCHUBERT"}]},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert duplicate.status_code == 409
    body = duplicate.json()
    assert body["code"] == "conflict_duplicate_song"
    assert body["conflicting_song_id"] == first_id
