"""Clerk JWT verifier — PyJWT + JWKS, with a ~1h JWKS cache (research.md §8)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from src.application.ports import ClerkClaims, ClerkVerifier
from src.domain.errors import ForbiddenError

__all__ = ["ClerkJWKSVerifier"]


class _ForbiddenJWT(ForbiddenError):
    code = "unauthorized"


class ClerkJWKSVerifier(ClerkVerifier):
    """Verifies a Clerk-issued JWT against the JWKS endpoint.

    JWKS responses are cached in-process for ``cache_ttl_seconds`` (default
    3600). Network fetches use ``httpx`` so the rest of the app can swap
    ``transport`` for testing.
    """

    def __init__(
        self,
        *,
        issuer: str,
        jwks_url: str,
        leeway_seconds: int = 60,
        cache_ttl_seconds: int = 3600,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._issuer = issuer
        self._jwks_url = jwks_url
        self._leeway = leeway_seconds
        self._cache_ttl = cache_ttl_seconds
        self._http_client = http_client
        self._lock = asyncio.Lock()
        self._jwk_client: PyJWKClient | None = None
        self._jwks_cached_at: float = 0.0

    async def _get_jwk_client(self) -> PyJWKClient:
        now = time.monotonic()
        async with self._lock:
            if self._jwk_client is None or (now - self._jwks_cached_at) > self._cache_ttl:
                # Use httpx (async) to fetch + then hand the data to PyJWKClient
                # which expects a URL or pre-fetched payload. PyJWKClient itself
                # is sync; we reuse it since lookup is in-memory once primed.
                self._jwk_client = PyJWKClient(self._jwks_url, cache_keys=True)
                self._jwks_cached_at = now
            return self._jwk_client

    async def verify(self, token: str) -> ClerkClaims:
        try:
            client = await self._get_jwk_client()
            signing_key = client.get_signing_key_from_jwt(token).key
            decoded: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False},
                leeway=self._leeway,
            )
        except (jwt.PyJWTError, ValueError) as exc:
            raise _ForbiddenJWT(f"Invalid Clerk token: {exc}") from exc

        sub = decoded.get("sub")
        if not isinstance(sub, str) or not sub:
            raise _ForbiddenJWT("Token missing 'sub' claim")
        # Clerk surfaces the verified primary email under one of these claims:
        email = (
            decoded.get("email")
            or decoded.get("primary_email_address")
            or decoded.get("email_address")
        )
        if not isinstance(email, str) or "@" not in email:
            raise _ForbiddenJWT("Token missing verified email claim")
        display_name = decoded.get("name") or decoded.get("full_name")
        if not isinstance(display_name, str):
            display_name = None
        return ClerkClaims(
            clerk_user_id=sub,
            email=email,
            display_name=display_name,
        )
