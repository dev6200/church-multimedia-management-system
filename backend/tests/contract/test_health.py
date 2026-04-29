"""Contract test for ``GET /healthz`` (T036)."""

from __future__ import annotations

import pytest


@pytest.mark.contract
async def test_healthz_returns_ok(client) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
