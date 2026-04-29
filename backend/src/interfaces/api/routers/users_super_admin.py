"""Super Admin user management endpoints (T134) — FR-005, FR-006."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.ports import Clock, UnitOfWork
from src.application.use_cases.role_management import DemoteUser, PromoteUser
from src.domain.entities import UserAccount
from src.domain.entities.user_account import CurrentUser
from src.domain.value_objects import Role
from src.interfaces.api.deps import get_clock, get_uow, require_role
from src.interfaces.api.schemas.users import (
    RoleUpdateRequestSchema,
    UserAccountPageSchema,
    UserAccountSchema,
)

router = APIRouter(prefix="/api/v1/super-admin/users", tags=["super-admin"])


def _user_to_schema(u: UserAccount) -> UserAccountSchema:
    return UserAccountSchema(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=u.role.value,
        created_at=u.created_at,
        updated_at=u.updated_at,
        version=u.version,
    )


def _parse_if_match(if_match: str | None) -> int:
    if if_match is None or not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "Role updates require the current user version in If-Match",
            },
        )
    cleaned = if_match.strip().strip('"')
    try:
        return int(cleaned)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "validation_error",
                "message": "If-Match must be an integer version",
            },
        ) from exc


@router.get("", response_model=UserAccountPageSchema)
async def list_users(
    actor: Annotated[CurrentUser, Depends(require_role(Role.SUPER_ADMIN))],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserAccountPageSchema:
    async with uow:
        result = await uow.users.list_paginated(page=page, page_size=page_size, q=q)
    return UserAccountPageSchema(
        items=[_user_to_schema(u) for u in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.put("/{user_id}/role", response_model=UserAccountSchema)
async def update_role(
    user_id: UUID,
    body: RoleUpdateRequestSchema,
    actor: Annotated[CurrentUser, Depends(require_role(Role.SUPER_ADMIN))],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> UserAccountSchema:
    expected_version = _parse_if_match(if_match)
    if body.role == "ADMIN":
        use_case = PromoteUser(uow=uow, clock=clock)
    else:
        use_case = DemoteUser(uow=uow, clock=clock)
    user = await use_case.execute(
        user_id, expected_version=expected_version, actor=actor
    )
    return _user_to_schema(user)
