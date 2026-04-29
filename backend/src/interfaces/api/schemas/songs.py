"""Pydantic schemas for the songs API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from src.interfaces.api.schemas.common import (
    ComposerSchema,
    OptionalFieldValueSchema,
    TaxonomyValueSchema,
)

__all__ = [
    "SongSummarySchema",
    "SongDetailSchema",
    "SongPageSchema",
    "ComposerInputSchema",
    "OptionalFieldInputSchema",
    "SongWriteRequestSchema",
]


class SongSummarySchema(BaseModel):
    id: UUID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    composers: list[ComposerSchema] = Field(min_length=1)
    seasons: list[TaxonomyValueSchema] = Field(default_factory=list)
    masses: list[TaxonomyValueSchema] = Field(default_factory=list)
    special_events: list[TaxonomyValueSchema] = Field(default_factory=list)
    version: int = Field(ge=1)


class SongDetailSchema(SongSummarySchema):
    optional_fields: list[OptionalFieldValueSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SongPageSchema(BaseModel):
    items: list[SongSummarySchema]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


# ---------------------------------------------------------------- write
class ComposerInputSchema(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]


class OptionalFieldInputSchema(BaseModel):
    definition_id: UUID
    value_url: Annotated[str, Field(min_length=1)]


class SongWriteRequestSchema(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    composers: list[ComposerInputSchema] = Field(min_length=1)
    season_ids: list[UUID] = Field(default_factory=list)
    mass_ids: list[UUID] = Field(default_factory=list)
    special_event_ids: list[UUID] = Field(default_factory=list)
    optional_fields: list[OptionalFieldInputSchema] = Field(default_factory=list)
