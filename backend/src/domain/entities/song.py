"""Song + Composer entities — data-model.md §2 & §3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.value_objects import ComposerName, DedupKey, LinkUrl

__all__ = ["Composer", "Song", "SongOptionalLink"]


@dataclass(slots=True)
class Composer:
    """A song author. Identity = ``name_norm``.

    Composers are created on-demand by ``CreateSong`` / ``UpdateSong`` use
    cases via a find-or-create on ``name_norm`` (data-model.md §3a).
    """

    id: UUID
    name: str
    name_norm: str
    created_at: datetime

    @classmethod
    def from_name(cls, *, id: UUID, name: ComposerName, now: datetime) -> "Composer":
        return cls(id=id, name=name.name, name_norm=name.norm, created_at=now)


@dataclass(slots=True)
class SongOptionalLink:
    """A populated optional-field value on a song. Bound to its definition by
    ``definition_id``. Absent rows mean "not provided" (FR-014, FR-025).
    """

    definition_id: UUID
    value: LinkUrl


@dataclass(slots=True)
class Song:
    """The core catalog entity (data-model.md §2).

    The ``dedup_key`` is owned by the domain (FR-009 / research.md §6) — the
    DB UNIQUE constraint is the safety net, but the rule lives here so the
    invariant is testable without I/O.
    """

    id: UUID
    title: str
    composer_ids: frozenset[UUID]
    composer_names: tuple[str, ...]
    taxonomy_value_ids: frozenset[UUID]
    optional_links: tuple[SongOptionalLink, ...]
    dedup_key: DedupKey
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    version: int = 1

    # ------------------------------------------------------------------ create
    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        title: str,
        composers: list[Composer],
        taxonomy_value_ids: frozenset[UUID],
        optional_links: tuple[SongOptionalLink, ...],
        actor_id: UUID,
        now: datetime,
    ) -> "Song":
        title_clean = title.strip()
        if not title_clean:
            raise ValueError("Title is required (FR-008)")
        if len(title_clean) > 200:
            raise ValueError("Title must be 1-200 characters")
        if not composers:
            raise ValueError("At least one composer is required (FR-008)")
        # FR-014: optional-field values must validate as URLs *before* we get here,
        # so SongOptionalLink already carries a LinkUrl. Just dedup definition_id.
        seen_defs: set[UUID] = set()
        for link in optional_links:
            if link.definition_id in seen_defs:
                raise ValueError(
                    f"Duplicate optional-field value for definition {link.definition_id}"
                )
            seen_defs.add(link.definition_id)
        composer_ids = frozenset(c.id for c in composers)
        composer_names = tuple(c.name for c in composers)
        dedup_key = DedupKey.compute(title_clean, [c.name_norm for c in composers])
        return cls(
            id=id,
            title=title_clean,
            composer_ids=composer_ids,
            composer_names=composer_names,
            taxonomy_value_ids=frozenset(taxonomy_value_ids),
            optional_links=tuple(optional_links),
            dedup_key=dedup_key,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            version=1,
        )

    # ------------------------------------------------------------------ update
    def update(
        self,
        *,
        title: str,
        composers: list[Composer],
        taxonomy_value_ids: frozenset[UUID],
        optional_links: tuple[SongOptionalLink, ...],
        actor_id: UUID,
        now: datetime,
    ) -> None:
        title_clean = title.strip()
        if not title_clean:
            raise ValueError("Title is required (FR-008)")
        if len(title_clean) > 200:
            raise ValueError("Title must be 1-200 characters")
        if not composers:
            raise ValueError("At least one composer is required (FR-008)")
        seen_defs: set[UUID] = set()
        for link in optional_links:
            if link.definition_id in seen_defs:
                raise ValueError(
                    f"Duplicate optional-field value for definition {link.definition_id}"
                )
            seen_defs.add(link.definition_id)
        self.title = title_clean
        self.composer_ids = frozenset(c.id for c in composers)
        self.composer_names = tuple(c.name for c in composers)
        self.taxonomy_value_ids = frozenset(taxonomy_value_ids)
        self.optional_links = tuple(optional_links)
        self.dedup_key = DedupKey.compute(title_clean, [c.name_norm for c in composers])
        self.updated_at = now
        self.updated_by = actor_id
        self.version += 1
