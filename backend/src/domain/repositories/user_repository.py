"""UserAccount repository ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from src.domain.entities import UserAccount
from src.domain.value_objects import Role

__all__ = [
    "UserPage",
    "UserRepository",
]


@dataclass(frozen=True, slots=True)
class UserPage:
    items: list[UserAccount]
    total: int
    page: int
    page_size: int


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> UserAccount | None: ...

    @abstractmethod
    async def get_by_clerk_id(self, clerk_user_id: str) -> UserAccount | None: ...

    @abstractmethod
    async def add(self, user: UserAccount) -> None: ...

    @abstractmethod
    async def list_paginated(
        self, *, page: int, page_size: int, q: str | None = None
    ) -> UserPage: ...

    @abstractmethod
    async def count_by_role(self, role: Role) -> int: ...

    @abstractmethod
    async def update_role_with_version(
        self, user: UserAccount, *, expected_version: int
    ) -> None:
        """Conditional UPDATE; raises ``VersionConflictError`` on zero rows."""
