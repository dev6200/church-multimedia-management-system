"""OptionalFieldDefinition repository ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities import OptionalFieldDefinition

__all__ = ["OptionalFieldRepository"]


class OptionalFieldRepository(ABC):
    @abstractmethod
    async def get_by_id(self, definition_id: UUID) -> OptionalFieldDefinition | None: ...

    @abstractmethod
    async def list_all(self) -> list[OptionalFieldDefinition]: ...

    @abstractmethod
    async def find_by_norm(self, label_norm: str) -> OptionalFieldDefinition | None: ...

    @abstractmethod
    async def add(self, definition: OptionalFieldDefinition) -> None: ...

    @abstractmethod
    async def rename_with_version(
        self, definition: OptionalFieldDefinition, *, expected_version: int
    ) -> None: ...

    @abstractmethod
    async def count_usage(self, definition_id: UUID) -> int: ...

    @abstractmethod
    async def delete_with_detach(self, definition_id: UUID, *, detach: bool) -> int:
        """Detach + delete; mirrors ``TaxonomyRepository.delete_with_detach``."""
