"""Shared Pydantic schemas used across multiple routers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "ComposerSchema",
    "TaxonomyValueSchema",
    "OptionalFieldDefinitionSchema",
    "OptionalFieldValueSchema",
]


class ComposerSchema(BaseModel):
    id: UUID
    name: str = Field(min_length=1, max_length=120)


class TaxonomyValueSchema(BaseModel):
    id: UUID
    kind: str
    name: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class OptionalFieldDefinitionSchema(BaseModel):
    id: UUID
    label: str = Field(min_length=1, max_length=60)
    kind: str
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class OptionalFieldValueSchema(BaseModel):
    definition_id: UUID
    label: str
    value_url: str
