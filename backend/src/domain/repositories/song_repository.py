"""Song repository ABC.

Lives in the domain layer; concrete SQLAlchemy implementation lives in
``src/infrastructure/db/repositories/song_repository.py``. Use cases depend on
this ABC, never on the concrete impl (Constitution Principle II).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from src.domain.entities import Composer, Song
from src.domain.queries.song_views import (
    SongDetailView,
    SongSummaryPage,
)
from src.domain.value_objects import DedupKey, TaxonomyKind

__all__ = [
    "SongFilters",
    "Pagination",
    "SongPage",
    "SongRepository",
]


def _empty_taxonomy_filter() -> dict[TaxonomyKind, frozenset[UUID]]:
    return {}


@dataclass(frozen=True, slots=True)
class SongFilters:
    """Filter set passed to ``SongRepository.search``.

    The ``q`` term is matched against title and composer name (FR-023).
    Taxonomy filter map is keyed by ``TaxonomyKind`` and contains a list of
    selected value-ids that combine as logical OR within a kind and AND across
    kinds (FR-024).
    """

    q: str | None = None
    taxonomy_value_ids_by_kind: dict[TaxonomyKind, frozenset[UUID]] = field(
        default_factory=_empty_taxonomy_filter
    )


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int = 1
    page_size: int = 20

    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class SongPage:
    items: list[Song]
    total: int
    page: int
    page_size: int


class SongRepository(ABC):
    """Persistence boundary for Song aggregate."""

    @abstractmethod
    async def get_by_id(self, song_id: UUID) -> Song | None: ...

    @abstractmethod
    async def find_by_dedup_key(self, dedup_key: DedupKey) -> Song | None: ...

    @abstractmethod
    async def find_composer_by_norm(self, name_norm: str) -> Composer | None:
        """Find-or-create-by-name: looks up a composer by its normalised name.

        ``name_norm`` is ``lower(trim(name))`` per data-model.md §3a.
        """

    @abstractmethod
    async def search(
        self, filters: SongFilters, pagination: Pagination
    ) -> SongPage: ...

    @abstractmethod
    async def add(self, song: Song, *, composers: list[Composer]) -> None: ...

    @abstractmethod
    async def update_with_version(
        self, song: Song, *, composers: list[Composer], expected_version: int
    ) -> None:
        """Conditional UPDATE … WHERE id=:id AND version=:expected.

        Implementation MUST raise ``VersionConflictError`` when zero rows are
        affected (FR-030).
        """

    @abstractmethod
    async def delete_with_version(
        self, song_id: UUID, *, expected_version: int
    ) -> None: ...

    # ---------------------------------------------------------- read views
    @abstractmethod
    async def search_summary_views(
        self, filters: SongFilters, pagination: Pagination
    ) -> SongSummaryPage:
        """Read-side: returns hydrated summaries for the catalog list page."""

    @abstractmethod
    async def get_detail_view(self, song_id: UUID) -> SongDetailView | None:
        """Read-side: returns the fully hydrated detail for a song, or None."""
