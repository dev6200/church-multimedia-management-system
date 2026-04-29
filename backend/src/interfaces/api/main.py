"""FastAPI application factory.

Maps domain errors to the stable error-code vocabulary defined in
``contracts/openapi.yaml``. Routers are registered here in dependency order
so contract tests don't need to import the modules in any particular sequence.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.errors import (
    ConflictError,
    DomainError,
    DuplicateSongError,
    ForbiddenError,
    LastSuperAdminError,
    NotFoundError,
    TaxonomyInUseError,
    VersionConflictError,
)
from src.interfaces.api.routers.auth_me import router as auth_me_router
from src.interfaces.api.routers.health import router as health_router
from src.interfaces.api.routers.optional_fields import router as optional_fields_router
from src.interfaces.api.routers.songs_admin import (
    router_admin_create as songs_admin_create_router,
    router_admin_mutate as songs_admin_mutate_router,
)
from src.interfaces.api.routers.songs_public import router as songs_public_router
from src.interfaces.api.routers.taxonomies import router as taxonomies_router
from src.interfaces.api.routers.users_super_admin import (
    router as super_admin_users_router,
)

__all__ = ["app", "create_app"]


# ----- Exception handlers (module-level so they're not flagged as unused) -----


def _error_payload(exc: DomainError) -> dict[str, Any]:
    return {"code": exc.code, "message": exc.message, **exc.details}


async def _on_not_found(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, NotFoundError)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=_error_payload(exc),
    )


async def _on_forbidden(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ForbiddenError)
    # ``unauthorized`` (Clerk JWT issues) is mapped to 401; everything else
    # forbidden is 403.
    if exc.code == "unauthorized":
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_payload(exc),
        )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=_error_payload(exc),
    )


async def _on_version_conflict(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, VersionConflictError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_payload(exc),
    )


async def _on_duplicate_song(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DuplicateSongError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_payload(exc),
    )


async def _on_taxonomy_in_use(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, TaxonomyInUseError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_payload(exc),
    )


async def _on_last_super_admin(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, LastSuperAdminError)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_payload(exc),
    )


async def _on_conflict_error(_: Request, exc: Exception) -> JSONResponse:
    # Catch-all for ConflictError subclasses (DuplicateTaxonomyValueError,
    # DuplicateOptionalFieldError, etc.) that don't have a more specific
    # handler registered above.
    assert isinstance(exc, ConflictError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_error_payload(exc),
    )


async def _on_domain_error(_: Request, exc: Exception) -> JSONResponse:
    # Catch-all for unmapped domain errors.
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_payload(exc),
    )


async def _on_value_error(_: Request, exc: Exception) -> JSONResponse:
    # Domain entities raise plain ValueError for invariant violations
    # (e.g. whitespace-only title). Map to 400 with a stable code so the
    # frontend can surface the message.
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "validation_error", "message": str(exc)},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Church Songlist Management",
        version="0.1.0",
        description="Catholic Church Songlist Management SaaS — backend API.",
    )

    # Register handlers explicitly — the function references are visible to
    # the type checker (decorators register the function but never re-read
    # the name, so Pylance's reportUnusedFunction would flag those).
    app.add_exception_handler(NotFoundError, _on_not_found)
    app.add_exception_handler(ForbiddenError, _on_forbidden)
    app.add_exception_handler(VersionConflictError, _on_version_conflict)
    app.add_exception_handler(DuplicateSongError, _on_duplicate_song)
    app.add_exception_handler(TaxonomyInUseError, _on_taxonomy_in_use)
    app.add_exception_handler(LastSuperAdminError, _on_last_super_admin)
    app.add_exception_handler(ConflictError, _on_conflict_error)
    app.add_exception_handler(DomainError, _on_domain_error)
    app.add_exception_handler(ValueError, _on_value_error)

    # ----- Routers ---------------------------------------------------------
    # NOTE: register the admin mutate router BEFORE the public songs router —
    # both mount paths under /api/v1/songs and FastAPI matches in order.
    # The admin router owns PUT/DELETE for /{id}; public owns GET.
    app.include_router(health_router)
    app.include_router(auth_me_router)
    app.include_router(songs_admin_create_router)
    app.include_router(songs_admin_mutate_router)
    app.include_router(songs_public_router)
    app.include_router(taxonomies_router)
    app.include_router(optional_fields_router)
    app.include_router(super_admin_users_router)

    return app


app = create_app()
