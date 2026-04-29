"""Clerk JWT verifier — application port.

Concrete implementation lives at
``src/infrastructure/auth/clerk_jwks_verifier.py``. Tests inject an in-memory
fake. Keeping this as a port lets contract tests use
``app.dependency_overrides`` to short-circuit JWT verification (research.md §14).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

__all__ = ["ClerkClaims", "ClerkVerifier"]


@dataclass(frozen=True, slots=True)
class ClerkClaims:
    """Subset of the Clerk JWT claims that the application cares about."""

    clerk_user_id: str  # ``sub``
    email: str
    display_name: str | None = None


class ClerkVerifier(ABC):
    @abstractmethod
    async def verify(self, token: str) -> ClerkClaims:
        """Validate signature, issuer, expiry; return claims.

        MUST raise ``ValueError`` (or a domain ``ForbiddenError`` subclass)
        when the token is missing/expired/wrong-issuer/wrong-signature so the
        FastAPI exception handler can map to 401.
        """
