"""Contract-test fixtures (T037 + T056 + T057 + T058 + T086 + T087 + T088).

Provides:
- A ``FakeClerkVerifier`` that returns canned ``ClerkClaims`` for any token.
- A shared ``InMemoryUnitOfWork`` (from ``tests/unit/fakes.py``) so contract
  tests can seed catalog data via the same fakes used by unit tests.
- A ``client`` fixture returning an ``httpx.AsyncClient`` against the FastAPI
  app with the dependencies overridden.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.ports import (
    ClerkClaims,
    ClerkVerifier,
    Clock,
)
from src.domain.entities import UserAccount
from src.domain.errors import ForbiddenError
from src.domain.value_objects import Role
from src.infrastructure.config import Settings, get_settings
from src.interfaces.api.deps import (
    get_clerk_verifier,
    get_clock,
    get_uow,
)
from src.interfaces.api.main import create_app
from tests.unit.fakes import InMemoryUnitOfWork


# ----------------------------------------------------------------- fakes


class FixedClock(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class FakeClerkVerifier(ClerkVerifier):
    """Pretends ``token`` IS the ``clerk_user_id``; resolves email + display
    from ``email_for`` map. Tests inject the map per scenario."""

    def __init__(self, *, email_for: dict[str, tuple[str, str | None]]) -> None:
        self._email_for = email_for

    async def verify(self, token: str) -> ClerkClaims:
        token = token.strip()
        if not token:
            raise ForbiddenError("Empty token")
        if token not in self._email_for:
            raise ForbiddenError(f"Unknown fake token: {token}")
        email, display = self._email_for[token]
        return ClerkClaims(clerk_user_id=token, email=email, display_name=display)


# ----------------------------------------------------------------- fixtures


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def super_admin_emails() -> str:
    return "boss@parish.example.org"


@pytest.fixture
def settings_override(super_admin_emails: str) -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        CLERK_JWT_ISSUER="https://test.clerk.accounts.dev",
        CLERK_JWKS_URL="https://test.clerk.accounts.dev/.well-known/jwks.json",
        SUPER_ADMIN_EMAILS=super_admin_emails,
    )


@pytest.fixture
def in_memory_uow() -> InMemoryUnitOfWork:
    """A single shared UoW instance for the whole test — every dependency
    override returns it so any seeding from the test itself survives across
    request cycles."""

    return InMemoryUnitOfWork()


@pytest.fixture
def users_store(in_memory_uow: InMemoryUnitOfWork):
    return in_memory_uow.users.store


@pytest.fixture
def songs_store(in_memory_uow: InMemoryUnitOfWork):
    return in_memory_uow.songs.store


@pytest.fixture
def taxonomies_store(in_memory_uow: InMemoryUnitOfWork):
    return in_memory_uow.taxonomies.store


@pytest.fixture
def optional_fields_store(in_memory_uow: InMemoryUnitOfWork):
    return in_memory_uow.optional_fields.store


@pytest.fixture
def fake_verifier_map() -> dict[str, tuple[str, str | None]]:
    """Default tokens for tests; individual tests can extend the dict."""

    return {
        "user-token": ("regular@parish.example.org", "Regular User"),
        "admin-token": ("admin@parish.example.org", "Admin"),
        "super-admin-token": ("boss@parish.example.org", "Super Admin"),
    }


@pytest.fixture
def fake_verifier(fake_verifier_map):
    return FakeClerkVerifier(email_for=fake_verifier_map)


def _seed_user(
    *,
    store: dict[UUID, UserAccount],
    clerk_user_id: str,
    email: str,
    role: Role,
    fixed_now: datetime,
) -> UserAccount:
    user = UserAccount(
        id=uuid4(),
        clerk_user_id=clerk_user_id,
        email=email,
        display_name=None,
        role=role,
        created_at=fixed_now,
        updated_at=fixed_now,
        version=1,
    )
    store[user.id] = user
    return user


@pytest.fixture
def seeded_admin(users_store, fixed_now: datetime) -> UserAccount:
    return _seed_user(
        store=users_store,
        clerk_user_id="admin-token",
        email="admin@parish.example.org",
        role=Role.ADMIN,
        fixed_now=fixed_now,
    )


@pytest.fixture
def seeded_super_admin(users_store, fixed_now: datetime) -> UserAccount:
    return _seed_user(
        store=users_store,
        clerk_user_id="super-admin-token",
        email="boss@parish.example.org",
        role=Role.SUPER_ADMIN,
        fixed_now=fixed_now,
    )


@pytest.fixture
def seeded_user(users_store, fixed_now: datetime) -> UserAccount:
    return _seed_user(
        store=users_store,
        clerk_user_id="user-token",
        email="regular@parish.example.org",
        role=Role.USER,
        fixed_now=fixed_now,
    )


@pytest.fixture
async def client(
    settings_override: Settings,
    in_memory_uow: InMemoryUnitOfWork,
    fake_verifier: FakeClerkVerifier,
    fixed_now: datetime,
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings_override

    async def _yield_uow():
        yield in_memory_uow

    app.dependency_overrides[get_uow] = _yield_uow
    app.dependency_overrides[get_clerk_verifier] = lambda: fake_verifier
    app.dependency_overrides[get_clock] = lambda: FixedClock(fixed_now)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
