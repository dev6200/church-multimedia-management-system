"""TaxonomyValue entity — data-model.md §4."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.value_objects import TaxonomyKind

__all__ = ["TaxonomyValue"]


@dataclass(slots=True)
class TaxonomyValue:
    """One value in one of the three taxonomies (Seasons / Masses / Special
    Events). Names are unique within their kind only — the same string can
    appear in different kinds (data-model.md §4)."""

    id: UUID
    kind: TaxonomyKind
    name: str
    name_norm: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        kind: TaxonomyKind,
        name: str,
        actor_id: UUID,
        now: datetime,
    ) -> "TaxonomyValue":
        clean = name.strip()
        if not clean:
            raise ValueError("Taxonomy value name must not be empty")
        if len(clean) > 80:
            raise ValueError("Taxonomy value name must be 1-80 characters")
        return cls(
            id=id,
            kind=kind,
            name=clean,
            name_norm=clean.lower(),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            version=1,
        )

    def rename(self, *, new_name: str, actor_id: UUID, now: datetime) -> None:
        clean = new_name.strip()
        if not clean:
            raise ValueError("Taxonomy value name must not be empty")
        if len(clean) > 80:
            raise ValueError("Taxonomy value name must be 1-80 characters")
        self.name = clean
        self.name_norm = clean.lower()
        self.updated_at = now
        self.updated_by = actor_id
        self.version += 1
