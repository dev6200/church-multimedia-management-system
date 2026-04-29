"""ORM models for TaxonomyValue and the song↔taxonomy association table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base

__all__ = ["TaxonomyValueModel", "SongTaxonomyValueLink", "taxonomy_kind_enum"]


taxonomy_kind_enum = ENUM(
    "SEASON",
    "MASS",
    "SPECIAL_EVENT",
    name="taxonomy_kind",
    create_type=False,
)


class TaxonomyValueModel(Base):
    __tablename__ = "taxonomy_values"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    kind: Mapped[str] = mapped_column(taxonomy_kind_enum, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_norm: Mapped[str] = mapped_column(CITEXT(), nullable=False)
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

    __table_args__ = (
        UniqueConstraint("kind", "name_norm", name="uq_taxonomy_values_kind_name_norm"),
    )


class SongTaxonomyValueLink(Base):
    __tablename__ = "song_taxonomy_values"

    song_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
    )
    taxonomy_value_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("taxonomy_values.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (PrimaryKeyConstraint("song_id", "taxonomy_value_id"),)
