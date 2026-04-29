"""Contract test for taxonomy admin endpoints (T109)."""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_create_taxonomy_value_returns_201(
    client, seeded_admin
) -> None:
    response = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "Christ the King"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Christ the King"
    assert body["kind"] == "SEASON"
    assert body["version"] == 1


@pytest.mark.contract
async def test_create_duplicate_returns_409(client, seeded_admin) -> None:
    payload = {"name": "Advent"}
    first = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json=payload,
        headers={"Authorization": "Bearer admin-token"},
    )
    assert first.status_code == 201

    duplicate = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "advent"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "conflict_duplicate_taxonomy_value"


@pytest.mark.contract
async def test_rename_requires_if_match(client, seeded_admin) -> None:
    create = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "Advent"},
        headers={"Authorization": "Bearer admin-token"},
    )
    value = create.json()
    response = await client.put(
        f"/api/v1/admin/taxonomies/seasons/{value['id']}",
        json={"name": "Renamed"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 428


@pytest.mark.contract
async def test_delete_in_use_without_detach_returns_409(
    client, seeded_admin, taxonomies_store, in_memory_uow
) -> None:
    create = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "Advent"},
        headers={"Authorization": "Bearer admin-token"},
    )
    value = create.json()
    # Pretend it's in use by 4 songs.
    from uuid import UUID

    in_memory_uow.taxonomies.usage[UUID(value["id"])] = 4

    response = await client.delete(
        f"/api/v1/admin/taxonomies/seasons/{value['id']}",
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": "1",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "conflict_taxonomy_in_use"
    assert body["usage_count"] == 4


@pytest.mark.contract
async def test_delete_with_detach_returns_204(
    client, seeded_admin, in_memory_uow
) -> None:
    create = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "Advent"},
        headers={"Authorization": "Bearer admin-token"},
    )
    value = create.json()
    from uuid import UUID

    in_memory_uow.taxonomies.usage[UUID(value["id"])] = 4

    response = await client.delete(
        f"/api/v1/admin/taxonomies/seasons/{value['id']}",
        params={"detach": "true"},
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": "1",
        },
    )
    assert response.status_code == 204


@pytest.mark.contract
async def test_usage_endpoint_returns_count(
    client, seeded_admin, in_memory_uow
) -> None:
    create = await client.post(
        "/api/v1/admin/taxonomies/seasons",
        json={"name": "Advent"},
        headers={"Authorization": "Bearer admin-token"},
    )
    value = create.json()
    from uuid import UUID

    in_memory_uow.taxonomies.usage[UUID(value["id"])] = 4

    response = await client.get(
        f"/api/v1/admin/taxonomies/seasons/{value['id']}/usage",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"usage_count": 4}
