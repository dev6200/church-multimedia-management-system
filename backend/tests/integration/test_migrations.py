"""Integration test (T038) — Alembic upgrade head produces full schema +
seeded rows on a real Postgres via testcontainers.

Skipped automatically when Docker / testcontainers cannot start (so unit
suites still run on machines without docker)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import sqlalchemy as sa

testcontainers = pytest.importorskip("testcontainers.postgres")

from sqlalchemy.ext.asyncio import create_async_engine

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.mark.integration
async def test_alembic_upgrade_head_produces_schema_and_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from testcontainers.postgres import PostgresContainer

    image = os.getenv("POSTGRES_IMAGE", "postgres:16-alpine")
    with PostgresContainer(image, driver=None) as pg:
        sync_url = pg.get_connection_url()  # postgresql+psycopg2://...
        async_url = sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg")

        # Point Alembic + Settings at the container.
        monkeypatch.setenv("DATABASE_URL", async_url)

        # Reset settings cache (lru_cache).
        from src.infrastructure import config as config_module

        config_module.get_settings.cache_clear()

        # Run the migration via Alembic API.
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)
        command.upgrade(alembic_cfg, "head")

        engine = create_async_engine(async_url, future=True)
        try:
            async with engine.connect() as conn:
                # All tables exist
                tables = (await conn.execute(
                    sa.text(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                    )
                )).scalars().all()
                expected = {
                    "user_accounts",
                    "composers",
                    "taxonomy_values",
                    "optional_field_definitions",
                    "songs",
                    "song_composers",
                    "song_taxonomy_values",
                    "song_optional_field_values",
                    "alembic_version",
                }
                assert expected.issubset(set(tables))

                # pg_trgm extension installed
                ext = (await conn.execute(
                    sa.text(
                        "SELECT extname FROM pg_extension WHERE extname='pg_trgm'"
                    )
                )).scalar_one_or_none()
                assert ext == "pg_trgm"

                # Seeds present (FR-020 / FR-021)
                seasons = (await conn.execute(
                    sa.text(
                        "SELECT name FROM taxonomy_values WHERE kind='SEASON' ORDER BY name"
                    )
                )).scalars().all()
                assert "Advent" in seasons
                assert "Christmas" in seasons
                assert "Lent" in seasons
                assert "Easter" in seasons
                assert "Ordinary Time" in seasons

                opt_fields = (await conn.execute(
                    sa.text("SELECT label FROM optional_field_definitions ORDER BY label")
                )).scalars().all()
                assert "PowerPoint link" in opt_fields
                assert "Sheet Music" in opt_fields
                assert "YouTube link" in opt_fields
                assert "Lyrics link" in opt_fields
        finally:
            await engine.dispose()
