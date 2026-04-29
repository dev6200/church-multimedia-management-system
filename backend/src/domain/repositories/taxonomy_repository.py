"""TaxonomyValue repository ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities import TaxonomyValue
from src.domain.value_objects import TaxonomyKind

__all__ = ["TaxonomyRepository"]


class TaxonomyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, value_id: UUID) -> TaxonomyValue | None: ...

    @abstractmethod
    async def list_by_kind(self, kind: TaxonomyKind) -> list[TaxonomyValue]: ...

    @abstractmethod
    async def find_by_kind_and_norm(
        self, kind: TaxonomyKind, name_norm: str
    ) -> TaxonomyValue | None: ...

    @abstractmethod
    async def add(self, value: TaxonomyValue) -> None: ...

    @abstractmethod
    async def rename_with_version(
        self, value: TaxonomyValue, *, expected_version: int
    ) -> None: ...

    @abstractmethod
    async def count_usage(self, value_id: UUID) -> int:
        """Number of songs currently referencing this taxonomy value (FR-019)."""

    @abstractmethod
    async def delete_with_detach(self, value_id: UUID, *, detach: bool) -> int:
        """Delete a taxonomy value.

        ``detach=False``: refuse if any song references it (raise
        ``TaxonomyInUseError`` carrying the usage count).
        ``detach=True``: in a single transaction, drop every association row,
        then delete the taxonomy value. Affected songs' ``updated_at`` /
        ``updated_by`` are bumped but their ``version`` is **not**
        incremented (data-model.md §6).

        Returns the number of detached associations.
        """
