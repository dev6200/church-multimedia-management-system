"""SQLAlchemy implementation of ``UnitOfWork`` (T029).

Holds an ``AsyncSession`` plus the four repository attributes required by the
abstract port. ``__aenter__`` opens a session; ``commit`` / ``rollback`` close
the active transaction; ``__aexit__`` always disposes the session.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ports import UnitOfWork
from src.infrastructure.db.repositories import (
    SqlAlchemyOptionalFieldRepository,
    SqlAlchemySongRepository,
    SqlAlchemyTaxonomyRepository,
    SqlAlchemyUserRepository,
)

__all__ = ["SqlAlchemyUnitOfWork"]


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        # Bind concrete repositories to the session.
        self.songs = SqlAlchemySongRepository(self._session)
        self.users = SqlAlchemyUserRepository(self._session)
        self.taxonomies = SqlAlchemyTaxonomyRepository(self._session)
        self.optional_fields = SqlAlchemyOptionalFieldRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None, "UoW not entered"
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None, "UoW not entered"
        await self._session.rollback()
