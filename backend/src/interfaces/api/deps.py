"""FastAPI dependency factories.

Wires the application ports + use cases through ``Depends(...)``. Tests
override individual factories via ``app.dependency_overrides`` (research.md
§14).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.application.ports import ClerkClaims, ClerkVerifier, Clock, SystemClock, UnitOfWork
from src.domain.entities import CurrentUser, UserAccount
from src.domain.errors import ForbiddenError
from src.domain.value_objects import Role
from src.infrastructure.auth.clerk_jwks_verifier import ClerkJWKSVerifier
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.db.base import get_session_factory
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

__all__ = [
    "get_clock",
    "get_clerk_verifier",
    "get_uow",
    "get_optional_bearer_token",
    "get_optional_current_user",
    "get_current_user",
    "require_role",
]


def get_clock() -> Clock:
    return SystemClock()


_verifier_singleton: ClerkVerifier | None = None


def get_clerk_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClerkVerifier:
    # Lazily build a process-level singleton — Pydantic settings are frozen so
    # the verifier never needs to be rebuilt mid-process. Using ``lru_cache``
    # would require ``Settings`` to be marked Hashable to the type checker,
    # which Pydantic v2 does at runtime but the stubs don't always advertise.
    global _verifier_singleton
    if _verifier_singleton is None:
        _verifier_singleton = ClerkJWKSVerifier(
            issuer=settings.CLERK_JWT_ISSUER,
            jwks_url=settings.CLERK_JWKS_URL,
            leeway_seconds=settings.CLERK_JWT_LEEWAY_SECONDS,
        )
    return _verifier_singleton


async def get_uow() -> AsyncIterator[UnitOfWork]:
    factory = get_session_factory()
    yield SqlAlchemyUnitOfWork(factory)


def get_optional_bearer_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def get_optional_current_user(
    token: Annotated[str | None, Depends(get_optional_bearer_token)],
    verifier: Annotated[ClerkVerifier, Depends(get_clerk_verifier)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CurrentUser | None:
    """Return the authenticated caller if a Bearer token is present and valid;
    otherwise return ``None``. Used by public read endpoints (FR-031) so they
    can also surface "you are signed in" hints if needed."""

    if token is None:
        return None
    try:
        claims = await verifier.verify(token)
    except ForbiddenError:
        return None
    async with uow:
        existing = await uow.users.get_by_clerk_id(claims.clerk_user_id)
        if existing is None:
            return None
        return _to_current_user(existing)


async def get_current_user(
    token: Annotated[str | None, Depends(get_optional_bearer_token)],
    verifier: Annotated[ClerkVerifier, Depends(get_clerk_verifier)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CurrentUser:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Bearer token required"},
        )
    try:
        claims = await verifier.verify(token)
    except ForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": exc.message},
        ) from exc
    async with uow:
        existing = await uow.users.get_by_clerk_id(claims.clerk_user_id)
    if existing is None:
        # The caller has a valid Clerk token but no provisioned local row yet.
        # Force them through ``GET /api/v1/auth/me`` first.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Account not provisioned — call GET /api/v1/auth/me first",
            },
        )
    return _to_current_user(existing)


def _to_current_user(account: UserAccount) -> CurrentUser:
    return CurrentUser(
        id=account.id,
        clerk_user_id=account.clerk_user_id,
        email=account.email,
        role=account.role,
    )


def require_role(*allowed: Role) -> Callable[..., Awaitable[CurrentUser]]:
    """Returns a FastAPI dependency that enforces RBAC (FR-004)."""

    allowed_set = frozenset(allowed)

    async def _checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "forbidden",
                    "message": f"Role {current_user.role} is not permitted",
                },
            )
        return current_user

    return _checker
