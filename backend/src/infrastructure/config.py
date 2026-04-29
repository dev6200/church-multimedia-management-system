"""Application configuration — pydantic-settings.

Reads from environment variables (12-factor) with optional ``.env`` support
for local development. The frozen ``Settings`` instance is exposed as a
process-level singleton via ``get_settings()`` and consumed through FastAPI's
dependency injection (see ``src/interfaces/api/deps.py``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        frozen=True,
    )

    # PostgreSQL — must use asyncpg driver for SQLAlchemy 2.x async.
    DATABASE_URL: str = "postgresql+asyncpg://app:app@db:5432/app"

    # Clerk — JWKS verification (see research.md §8).
    CLERK_JWT_ISSUER: str = ""
    CLERK_JWKS_URL: str = ""

    # Comma-separated email allowlist for FR-007.
    SUPER_ADMIN_EMAILS: str = ""

    # Optional — JWT clock skew tolerance in seconds.
    CLERK_JWT_LEEWAY_SECONDS: int = 60

    @property
    def super_admin_email_set(self) -> frozenset[str]:
        return frozenset(
            e.strip().lower() for e in self.SUPER_ADMIN_EMAILS.split(",") if e.strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
