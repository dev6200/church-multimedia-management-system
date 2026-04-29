"""Contract test for ``GET /api/v1/auth/me`` (T037).

Covers FR-001, FR-007, FR-031:
- Anonymous → 401.
- First valid Clerk token for an unknown user provisions a USER row.
- A token whose email is on the SUPER_ADMIN_EMAILS allowlist provisions
  directly as SUPER_ADMIN.
"""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_anonymous_returns_401(client) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "unauthorized"


@pytest.mark.contract
async def test_first_sign_in_provisions_user_role(
    client, users_store
) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer user-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["clerk_user_id"] == "user-token"
    assert body["email"] == "regular@parish.example.org"
    assert body["role"] == "USER"
    # Persisted in the in-memory store.
    assert len(users_store) == 1


@pytest.mark.contract
async def test_first_sign_in_with_allowlisted_email_provisions_super_admin(
    client, users_store
) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer super-admin-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "boss@parish.example.org"
    assert body["role"] == "SUPER_ADMIN"
    assert len(users_store) == 1


@pytest.mark.contract
async def test_returning_user_is_not_re_provisioned(client, users_store) -> None:
    # First call provisions.
    first = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer user-token"},
    )
    assert first.status_code == 200
    assert len(users_store) == 1
    first_user = next(iter(users_store.values()))

    # Second call returns the SAME user, no duplicate row.
    second = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer user-token"},
    )
    assert second.status_code == 200
    assert len(users_store) == 1
    assert second.json()["id"] == str(first_user.id)


@pytest.mark.contract
async def test_invalid_token_returns_401(client) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-known-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"
