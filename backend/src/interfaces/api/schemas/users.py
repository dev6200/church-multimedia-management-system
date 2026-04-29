"""Pydantic schemas for user-account endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "UserAccountSchema",
    "UserAccountPageSchema",
    "RoleUpdateRequestSchema",
]


class UserAccountSchema(BaseModel):
    id: UUID
    # Email is validated upstream by Clerk and pulled from the verified JWT
    # claim (data-model.md §1) — the API never receives an unvalidated email
    # so plain `str` is sufficient and avoids the `email-validator` dep.
    email: str
    display_name: str | None
    role: str
    created_at: datetime
    updated_at: datetime
    version: int = Field(ge=1)


class UserAccountPageSchema(BaseModel):
    items: list[UserAccountSchema]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class RoleUpdateRequestSchema(BaseModel):
    role: Literal["USER", "ADMIN"]
