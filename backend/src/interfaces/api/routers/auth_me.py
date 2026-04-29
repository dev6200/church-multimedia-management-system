"""``GET /api/v1/auth/me`` — verifies the Bearer JWT and returns the local
account, provisioning it on first sign-in (FR-007)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.application.ports import ClerkVerifier, Clock, UnitOfWork
from src.application.use_cases.provision_user import ProvisionUserOnFirstSignIn
from src.domain.errors import ForbiddenError
from src.domain.value_objects import Role
from src.infrastructure.config import Settings, get_settings
from src.interfaces.api.deps import (
    get_clerk_verifier,
    get_clock,
    get_optional_bearer_token,
    get_uow,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    id: UUID
    clerk_user_id: str
    email: str
    display_name: str | None
    role: Role
    created_at: datetime
    updated_at: datetime
    version: int


@router.get("/me", response_model=CurrentUserResponse)
async def auth_me(
    token: Annotated[str | None, Depends(get_optional_bearer_token)],
    verifier: Annotated[ClerkVerifier, Depends(get_clerk_verifier)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
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

    use_case = ProvisionUserOnFirstSignIn(
        uow=uow,
        clock=clock,
        super_admin_emails=settings.super_admin_email_set,
    )
    result = await use_case.execute(claims)
    user = result.user
    return CurrentUserResponse(
        id=user.id,
        clerk_user_id=user.clerk_user_id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
        version=user.version,
    )
