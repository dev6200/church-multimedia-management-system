"""Domain error hierarchy.

The infrastructure / interfaces layers map these to HTTP status codes and the
stable error-code vocabulary defined in ``contracts/openapi.yaml``. The domain
layer never imports HTTP types — it only raises these.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

__all__ = [
    "DomainError",
    "ConflictError",
    "NotFoundError",
    "ForbiddenError",
    "VersionConflictError",
    "DuplicateSongError",
    "DuplicateTaxonomyValueError",
    "DuplicateOptionalFieldError",
    "LastSuperAdminError",
    "TaxonomyInUseError",
]


class DomainError(Exception):
    """Base class for all domain-level errors."""

    code: str = "domain_error"

    def __init__(self, message: str, /, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class ForbiddenError(DomainError):
    code = "forbidden"


class VersionConflictError(ConflictError):
    """Optimistic-concurrency failure (FR-030)."""

    code = "conflict_version"

    def __init__(
        self,
        message: str = "Version conflict — refresh and retry",
        /,
        *,
        expected_version: int | None = None,
    ) -> None:
        super().__init__(message, expected_version=expected_version)


class DuplicateSongError(ConflictError):
    """A song with the same (title, composer set) already exists (FR-009)."""

    code = "conflict_duplicate_song"

    def __init__(self, message: str, /, *, conflicting_song_id: UUID) -> None:
        # Stringify for JSON serialisation; keep the typed attribute for
        # callers that want the UUID back.
        super().__init__(message, conflicting_song_id=str(conflicting_song_id))
        self.conflicting_song_id = conflicting_song_id


class LastSuperAdminError(DomainError):
    """Refused: would leave the system without any Super Admin (FR-006)."""

    code = "last_super_admin"


class TaxonomyInUseError(ConflictError):
    """Tried to delete a taxonomy / optional-field value still in use without
    detach (FR-019)."""

    code = "conflict_taxonomy_in_use"

    def __init__(self, message: str, /, *, usage_count: int) -> None:
        super().__init__(message, usage_count=usage_count)
        self.usage_count = usage_count


class DuplicateTaxonomyValueError(ConflictError):
    """A taxonomy value with the same (kind, name_norm) already exists."""

    code = "conflict_duplicate_taxonomy_value"

    def __init__(self, message: str, /, *, existing_id: UUID) -> None:
        super().__init__(message, existing_id=str(existing_id))
        self.existing_id = existing_id


class DuplicateOptionalFieldError(ConflictError):
    """An optional-field definition with the same label already exists."""

    code = "conflict_duplicate_optional_field"

    def __init__(self, message: str, /, *, existing_id: UUID) -> None:
        super().__init__(message, existing_id=str(existing_id))
        self.existing_id = existing_id
