"""UnitOfWork port — bundles repositories under one transaction.

Use cases acquire a ``UnitOfWork`` via DI, mutate aggregates through the
repositories it exposes, and commit. Concrete impl is
``SqlAlchemyUnitOfWork`` (infrastructure layer); tests use an in-memory fake.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from src.domain.repositories import (
    OptionalFieldRepository,
    SongRepository,
    TaxonomyRepository,
    UserRepository,
)

__all__ = ["UnitOfWork"]


class UnitOfWork(ABC):
    """Async context manager that scopes a transaction.

    Sample usage::

        async with uow:
            song = await uow.songs.get_by_id(id)
            ...
            await uow.commit()
    """

    songs: SongRepository
    users: UserRepository
    taxonomies: TaxonomyRepository
    optional_fields: OptionalFieldRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
