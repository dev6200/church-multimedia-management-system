"""ORM model for UserAccount."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base

__all__ = ["UserAccountModel", "user_role_enum"]


user_role_enum = ENUM(
    "SUPER_ADMIN",
    "ADMIN",
    "USER",
    name="user_role",
    create_type=False,
)


class UserAccountModel(Base):
    __tablename__ = "user_accounts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    clerk_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(user_role_enum, nullable=False, default="USER")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
