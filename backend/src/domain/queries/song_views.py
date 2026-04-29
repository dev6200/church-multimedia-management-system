"""Read-side view DTOs for the catalog browse / detail flows.

Per `data-model.md` §8 the User-facing read path joins Song + Composer +
TaxonomyValue + OptionalFieldDefinition. These dataclasses carry the result
of that join in a shape that the API schemas can serialise directly.

They live in the application layer (alongside use cases) so the domain layer
remains pure-Python aggregates focused on write-side invariants.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

__all__ = [
    "ComposerView",
    "TaxonomyValueView",
    "OptionalFieldValueView",
    "SongSummaryView",
    "SongDetailView",
    "SongSummaryPage",
]


@dataclass(frozen=True, slots=True)
class ComposerView:
    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class TaxonomyValueView:
    id: UUID
    kind: str  # 'SEASON' | 'MASS' | 'SPECIAL_EVENT'
    name: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OptionalFieldValueView:
    definition_id: UUID
    label: str  # mirrors the definition's CURRENT label (FR-018 rename preserves value)
    value_url: str


@dataclass(frozen=True, slots=True)
class SongSummaryView:
    id: UUID
    title: str
    composers: tuple[ComposerView, ...]
    seasons: tuple[TaxonomyValueView, ...]
    masses: tuple[TaxonomyValueView, ...]
    special_events: tuple[TaxonomyValueView, ...]
    version: int


@dataclass(frozen=True, slots=True)
class SongDetailView:
    id: UUID
    title: str
    composers: tuple[ComposerView, ...]
    seasons: tuple[TaxonomyValueView, ...]
    masses: tuple[TaxonomyValueView, ...]
    special_events: tuple[TaxonomyValueView, ...]
    optional_fields: tuple[OptionalFieldValueView, ...]
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SongSummaryPage:
    items: list[SongSummaryView]
    total: int
    page: int
    page_size: int
