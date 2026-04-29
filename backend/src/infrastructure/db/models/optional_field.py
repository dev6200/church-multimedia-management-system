"""ORM models for OptionalFieldDefinition + SongOptionalFieldValue."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base

__all__ = [
    "OptionalFieldDefinitionModel",
    "SongOptionalFieldValueModel",
    "optional_field_kind_enum",
]


optional_field_kind_enum = ENUM(
    "LINK",
    name="optional_field_kind",
    create_type=False,
)


class OptionalFieldDefinitionModel(Base):
    __tablename__ = "optional_field_definitions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    label_norm: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(
        optional_field_kind_enum, nullable=False, default="LINK"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SongOptionalFieldValueModel(Base):
    __tablename__ = "song_optional_field_values"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    song_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
    )
    definition_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("optional_field_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    value_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "song_id",
            "definition_id",
            name="uq_song_optional_field_values_song_definition",
        ),
    )
