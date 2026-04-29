"""Async SQLAlchemy engine + declarative ``Base`` + session factory.

The engine is a process-level singleton built from ``Settings.DATABASE_URL``.
Tests override ``Settings`` via ``app.dependency_overrides`` and rebuild the
engine to point at a testcontainers Postgres instance (research.md §14).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.infrastructure.config import get_settings

__all__ = [
    "Base",
    "build_engine",
    "build_session_factory",
    "get_engine",
    "get_session_factory",
    "get_session",
]


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def build_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings().DATABASE_URL)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = build_session_factory(get_engine())
    return cast(async_sessionmaker[AsyncSession], _session_factory)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a per-request session.

    Use only when a UoW is overkill (e.g. read-only health check). Most use
    cases should depend on ``UnitOfWork`` instead.
    """

    factory = get_session_factory()
    async with factory() as session:
        yield session
