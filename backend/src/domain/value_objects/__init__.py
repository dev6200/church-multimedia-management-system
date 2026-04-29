"""Domain value objects.

Pure-Python — no FastAPI / SQLAlchemy / Pydantic imports allowed here
(Constitution Principle II + research.md §2). Anything that needs to validate
or normalise input before it reaches an entity goes here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

__all__ = [
    "Role",
    "TaxonomyKind",
    "ComposerName",
    "LinkUrl",
    "DedupKey",
]


class Role(StrEnum):
    """Authorisation role assigned to a UserAccount (FR-002)."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


class TaxonomyKind(StrEnum):
    """The three independent taxonomies — FR-015."""

    SEASON = "SEASON"
    MASS = "MASS"
    SPECIAL_EVENT = "SPECIAL_EVENT"


@dataclass(frozen=True, slots=True)
class ComposerName:
    """A composer's display name plus its normalised lookup form.

    Per data-model.md §3a: ``name`` is the display form; ``norm`` is
    ``lower(trim(name))`` and is the unique key used for find-or-create.
    """

    name: str
    norm: str

    @classmethod
    def parse(cls, raw: str) -> "ComposerName":
        trimmed = raw.strip()
        if not trimmed:
            raise ValueError("Composer name must not be empty")
        if len(trimmed) > 120:
            raise ValueError("Composer name must be 1-120 characters")
        return cls(name=trimmed, norm=trimmed.lower())


@dataclass(frozen=True, slots=True)
class LinkUrl:
    """An absolute http(s) URL — FR-016.

    The domain validates the URL **before** persistence so the rule is owned by
    the domain rather than the HTTP / ORM layer.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> "LinkUrl":
        trimmed = raw.strip()
        if not trimmed:
            raise ValueError("URL must not be empty")
        parsed = urlparse(trimmed)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http:// or https://")
        if not parsed.netloc:
            raise ValueError("URL must include a host")
        return cls(value=trimmed)


@dataclass(frozen=True, slots=True)
class DedupKey:
    """SHA-256 hash of (lower-trimmed-title | sorted unique lower-trimmed composer names).

    Implements FR-009 — the (title, composer set) uniqueness invariant. The
    hash makes the comparison case-insensitive, whitespace-insensitive, and
    composer-order-insensitive while remaining a single TEXT column with a
    DB-enforced UNIQUE constraint (research.md §6).
    """

    value: str

    @classmethod
    def compute(cls, title: str, composer_names: list[str] | set[str]) -> "DedupKey":
        norm_title = title.strip().lower()
        if not norm_title:
            raise ValueError("Title must not be empty when computing DedupKey")
        norm_composers = sorted({c.strip().lower() for c in composer_names if c.strip()})
        if not norm_composers:
            raise ValueError("At least one composer is required when computing DedupKey")
        payload = f"{norm_title}|{','.join(norm_composers)}".encode("utf-8")
        return cls(value=hashlib.sha256(payload).hexdigest())
