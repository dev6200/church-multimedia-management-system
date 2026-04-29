"""RBAC audit (T143) — SC-006.

Walks every privileged endpoint and asserts:
- Anonymous request → 401 unauthorized.
- Authenticated USER role → 403 forbidden (or 401 if the route also requires
  super-admin and the user isn't provisioned — but for our seeded fixtures
  USER is always provisioned).

This test is intentionally a list / table-driven sweep so adding a new
privileged endpoint forces the author to update the table.
"""

from __future__ import annotations

from uuid import uuid4

import pytest


# ---------------------------------------------------------------- table

# Each entry: (METHOD, PATH, MIN_ROLE, body_required)
PRIVILEGED_ENDPOINTS: list[tuple[str, str, str, bool]] = [
    # Songs
    ("POST", "/api/v1/admin/songs", "ADMIN", True),
    ("PUT", f"/api/v1/songs/{uuid4()}", "ADMIN", True),
    ("DELETE", f"/api/v1/songs/{uuid4()}", "ADMIN", False),
    # Taxonomies
    ("POST", "/api/v1/admin/taxonomies/seasons", "ADMIN", True),
    ("PUT", f"/api/v1/admin/taxonomies/seasons/{uuid4()}", "ADMIN", True),
    ("DELETE", f"/api/v1/admin/taxonomies/seasons/{uuid4()}", "ADMIN", False),
    ("GET", f"/api/v1/admin/taxonomies/seasons/{uuid4()}/usage", "ADMIN", False),
    # Optional fields
    ("POST", "/api/v1/admin/optional-fields", "ADMIN", True),
    ("PUT", f"/api/v1/admin/optional-fields/{uuid4()}", "ADMIN", True),
    ("DELETE", f"/api/v1/admin/optional-fields/{uuid4()}", "ADMIN", False),
    ("GET", f"/api/v1/admin/optional-fields/{uuid4()}/usage", "ADMIN", False),
    # Super Admin user mgmt
    ("GET", "/api/v1/super-admin/users", "SUPER_ADMIN", False),
    ("PUT", f"/api/v1/super-admin/users/{uuid4()}/role", "SUPER_ADMIN", True),
]


def _body_for(method: str, path: str, body_required: bool) -> dict | None:
    if not body_required:
        return None
    if "/admin/songs" in path and method == "POST":
        return {"title": "x", "composers": [{"name": "y"}]}
    if "/songs/" in path and method == "PUT":
        return {"title": "x", "composers": [{"name": "y"}]}
    if "/taxonomies/" in path:
        return {"name": "x"}
    if "/optional-fields" in path:
        return {"label": "x"}
    if "/role" in path:
        return {"role": "USER"}
    return {}


@pytest.mark.contract
@pytest.mark.parametrize("method, path, _min_role, body_required", PRIVILEGED_ENDPOINTS)
async def test_anonymous_returns_401(client, method, path, _min_role, body_required) -> None:
    body = _body_for(method, path, body_required)
    response = await client.request(method, path, json=body)
    assert response.status_code == 401, (
        f"{method} {path} expected 401 anonymous; got {response.status_code}: {response.text}"
    )


@pytest.mark.contract
@pytest.mark.parametrize("method, path, min_role, body_required", PRIVILEGED_ENDPOINTS)
async def test_under_privileged_role_returns_403(
    client, seeded_user, seeded_admin, method, path, min_role, body_required
) -> None:
    body = _body_for(method, path, body_required)
    headers = {
        "Authorization": "Bearer admin-token" if min_role == "SUPER_ADMIN" else "Bearer user-token",
    }
    if method in ("PUT", "DELETE"):
        headers["If-Match"] = "1"
    response = await client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403, (
        f"{method} {path} with under-privileged role expected 403; got "
        f"{response.status_code}: {response.text}"
    )
