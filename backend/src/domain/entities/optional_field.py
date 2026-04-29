"""OptionalFieldDefinition + SongOptionalFieldValue entities — data-model.md §5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.domain.value_objects import LinkUrl

__all__ = [
    "OptionalFieldKind",
    "OptionalFieldDefinition",
    "OptionalFieldValue",
]


class OptionalFieldKind(StrEnum):
    """Open-ended kind discriminator. v1 supports only LINK (FR-016)."""

    LINK = "LINK"


@dataclass(slots=True)
class OptionalFieldDefinition:
    """An admin-defined optional field (e.g. "PowerPoint link", "Sheet Music")."""

    id: UUID
    label: str
    label_norm: str
    kind: OptionalFieldKind
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
        label: str,
        actor_id: UUID,
        now: datetime,
        kind: OptionalFieldKind = OptionalFieldKind.LINK,
    ) -> "OptionalFieldDefinition":
        clean = label.strip()
        if not clean:
            raise ValueError("Optional-field label must not be empty")
        if len(clean) > 60:
            raise ValueError("Optional-field label must be 1-60 characters")
        return cls(
            id=id,
            label=clean,
            label_norm=clean.lower(),
            kind=kind,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            version=1,
        )

    def rename(self, *, new_label: str, actor_id: UUID, now: datetime) -> None:
        """Rename preserves all per-song values (spec edge case + FR-018)."""

        clean = new_label.strip()
        if not clean:
            raise ValueError("Optional-field label must not be empty")
        if len(clean) > 60:
            raise ValueError("Optional-field label must be 1-60 characters")
        self.label = clean
        self.label_norm = clean.lower()
        self.updated_at = now
        self.updated_by = actor_id
        self.version += 1


@dataclass(slots=True)
class OptionalFieldValue:
    """Per-song, per-definition populated link value."""

    id: UUID
    song_id: UUID
    definition_id: UUID
    value: LinkUrl
    created_at: datetime
    updated_at: datetime
