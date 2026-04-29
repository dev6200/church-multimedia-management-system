"""Performance benchmark (T141) — SC-002.

Seeds 5,000 songs against a real Postgres (via testcontainers) and asserts
that p95 of `SongRepository.search_summary_views` is under 200ms server-time.

Skipped when testcontainers / Docker is unavailable.
"""

from __future__ import annotations

import os
import statistics
import time
from uuid import uuid4

import pytest

testcontainers = pytest.importorskip("testcontainers.postgres")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.use_cases.create_song import (
    CreateSong,
    CreateSongInput,
)
from src.domain.entities.user_account import CurrentUser, UserAccount
from src.domain.repositories import Pagination, SongFilters
from src.domain.value_objects import Role
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from src.application.ports import SystemClock


@pytest.mark.integration
async def test_search_p95_under_200ms_at_5k_songs(monkeypatch) -> None:
    from testcontainers.postgres import PostgresContainer

    image = os.getenv("POSTGRES_IMAGE", "postgres:16-alpine")
    with PostgresContainer(image, driver=None) as pg:
        async_url = pg.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+asyncpg"
        )
        monkeypatch.setenv("DATABASE_URL", async_url)
        from src.infrastructure import config as config_module

        config_module.get_settings.cache_clear()

        # Run migrations.
        from alembic import command
        from alembic.config import Config
        from pathlib import Path

        alembic_cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)
        command.upgrade(alembic_cfg, "head")

        engine = create_async_engine(async_url, future=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Seed an admin and 5,000 songs.
        actor_id = uuid4()
        async with session_factory() as session:
            from datetime import datetime, timezone
            from src.infrastructure.db.models import UserAccountModel

            session.add(
                UserAccountModel(
                    id=actor_id,
                    clerk_user_id="perf-admin",
                    email="perf-admin@parish.example.org",
                    role="ADMIN",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    version=1,
                )
            )
            await session.commit()

        actor = CurrentUser(
            id=actor_id,
            clerk_user_id="perf-admin",
            email="perf-admin@parish.example.org",
            role=Role.ADMIN,
        )

        for i in range(5000):
            uow = SqlAlchemyUnitOfWork(session_factory)
            use_case = CreateSong(uow=uow, clock=SystemClock())
            await use_case.execute(
                CreateSongInput(
                    title=f"Hymn {i:05d}",
                    composer_names=(f"Composer {i % 200}",),
                    season_ids=frozenset(),
                    mass_ids=frozenset(),
                    special_event_ids=frozenset(),
                    optional_links=(),
                ),
                actor=actor,
            )

        # Run 100 search queries and measure server-time.
        latencies_ms: list[float] = []
        uow = SqlAlchemyUnitOfWork(session_factory)
        for i in range(100):
            term = f"{i % 100:02d}"
            start = time.perf_counter()
            async with uow:
                await uow.songs.search_summary_views(
                    SongFilters(q=term),
                    Pagination(page=1, page_size=20),
                )
            latencies_ms.append((time.perf_counter() - start) * 1000)

        await engine.dispose()

        p95 = statistics.quantiles(latencies_ms, n=20)[-1]
        assert p95 < 200, f"p95 search latency {p95:.1f}ms exceeds 200ms budget (SC-002)"
