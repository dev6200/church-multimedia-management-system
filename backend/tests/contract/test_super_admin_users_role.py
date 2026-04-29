"""Contract test for ``PUT /api/v1/super-admin/users/{id}/role`` (T128)."""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_promote_user_to_admin(
    client, seeded_super_admin, seeded_user
) -> None:
    response = await client.put(
        f"/api/v1/super-admin/users/{seeded_user.id}/role",
        json={"role": "ADMIN"},
        headers={
            "Authorization": "Bearer super-admin-token",
            "If-Match": str(seeded_user.version),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "ADMIN"
    assert body["version"] == seeded_user.version + 1


@pytest.mark.contract
async def test_demote_admin_to_user(
    client, seeded_super_admin, seeded_admin
) -> None:
    response = await client.put(
        f"/api/v1/super-admin/users/{seeded_admin.id}/role",
        json={"role": "USER"},
        headers={
            "Authorization": "Bearer super-admin-token",
            "If-Match": str(seeded_admin.version),
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "USER"


@pytest.mark.contract
async def test_role_update_rejects_super_admin_in_payload(
    client, seeded_super_admin, seeded_admin
) -> None:
    response = await client.put(
        f"/api/v1/super-admin/users/{seeded_admin.id}/role",
        json={"role": "SUPER_ADMIN"},
        headers={
            "Authorization": "Bearer super-admin-token",
            "If-Match": str(seeded_admin.version),
        },
    )
    # Pydantic Literal["USER","ADMIN"] enforces this.
    assert response.status_code == 422


@pytest.mark.contract
async def test_role_update_requires_if_match(
    client, seeded_super_admin, seeded_user
) -> None:
    response = await client.put(
        f"/api/v1/super-admin/users/{seeded_user.id}/role",
        json={"role": "ADMIN"},
        headers={"Authorization": "Bearer super-admin-token"},
    )
    assert response.status_code == 428


@pytest.mark.contract
async def test_admin_role_returns_403(
    client, seeded_super_admin, seeded_admin, seeded_user
) -> None:
    response = await client.put(
        f"/api/v1/super-admin/users/{seeded_user.id}/role",
        json={"role": "ADMIN"},
        headers={
            "Authorization": "Bearer admin-token",
            "If-Match": str(seeded_user.version),
        },
    )
    assert response.status_code == 403
