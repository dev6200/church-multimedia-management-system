"""Contract test for ``GET /api/v1/super-admin/users`` (T127)."""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_list_users_requires_super_admin(client, seeded_admin) -> None:
    response = await client.get(
        "/api/v1/super-admin/users",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 403


@pytest.mark.contract
async def test_super_admin_can_list_users(
    client, seeded_super_admin, seeded_admin, seeded_user
) -> None:
    response = await client.get(
        "/api/v1/super-admin/users",
        headers={"Authorization": "Bearer super-admin-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    emails = {u["email"] for u in body["items"]}
    assert {
        "boss@parish.example.org",
        "admin@parish.example.org",
        "regular@parish.example.org",
    } <= emails


@pytest.mark.contract
async def test_anonymous_returns_401(client) -> None:
    response = await client.get("/api/v1/super-admin/users")
    assert response.status_code == 401


@pytest.mark.contract
async def test_q_filters_users(
    client, seeded_super_admin, seeded_admin, seeded_user
) -> None:
    response = await client.get(
        "/api/v1/super-admin/users",
        params={"q": "regular"},
        headers={"Authorization": "Bearer super-admin-token"},
    )
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()["items"]}
    assert emails == {"regular@parish.example.org"}
