"""Shared pytest fixtures.

Per `quickstart.md` §6 the suite has three tiers:
- ``tests/unit/`` runs the domain + application against in-memory fakes of
  repository ABCs (no I/O).
- ``tests/integration/`` runs SQLAlchemy + Alembic against a real Postgres
  via ``testcontainers``.
- ``tests/contract/`` runs the FastAPI app via ``httpx.AsyncClient`` with the
  Clerk verifier overridden through ``app.dependency_overrides``.

This module hosts only fixtures that every tier may use.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()
