"""Contract test for optional-field admin endpoints (T110)."""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_create_optional_field_returns_201(client, seeded_admin) -> None:
    response = await client.post(
        "/api/v1/admin/optional-fields",
        json={"label": "Spotify link"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["label"] == "Spotify link"
    assert body["kind"] == "LINK"


@pytest.mark.contract
async def test_create_duplicate_returns_409(client, seeded_admin) -> None:
    payload = {"label": "Spotify link"}
    first = await client.post(
        "/api/v1/admin/optional-fields",
        json=payload,
        headers={"Authorization": "Bearer admin-token"},
    )
    assert first.status_code == 201

    duplicate = await client.post(
        "/api/v1/admin/optional-fields",
        json={"label": "spotify link"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "conflict_duplicate_optional_field"


@pytest.mark.contract
async def test_rename_optional_field(client, seeded_admin) -> None:
    create = await client.post(
        "/api/v1/admin/optional-fields",
        json={"label": "PowerPoint link"},
        headers={"Authorization": "Bearer admin-token"},
    )
    field = create.json()
    rename = await client.put(
        f"/api/v1/admin/optional-fields/{field['id']}",
        json={"label": "Slides link"},
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(field["version"]),
        },
    )
    assert rename.status_code == 200
    assert rename.json()["label"] == "Slides link"


@pytest.mark.contract
async def test_delete_in_use_without_detach_returns_409(
    client, seeded_admin, in_memory_uow
) -> None:
    create = await client.post(
        "/api/v1/admin/optional-fields",
        json={"label": "PowerPoint link"},
        headers={"Authorization": "Bearer admin-token"},
    )
    field = create.json()
    from uuid import UUID

    in_memory_uow.optional_fields.usage[UUID(field["id"])] = 2

    response = await client.delete(
        f"/api/v1/admin/optional-fields/{field['id']}",
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": "1",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict_taxonomy_in_use"
