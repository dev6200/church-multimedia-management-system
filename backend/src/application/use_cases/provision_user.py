"""ProvisionUserOnFirstSignIn use case — FR-007.

The first time a Clerk JWT for an unknown ``clerk_user_id`` is presented to
the API, this use case mirrors the Clerk identity into a local
``user_accounts`` row, auto-promoting to ``SUPER_ADMIN`` when the verified
email is on the configured allowlist.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.ports import ClerkClaims, Clock, UnitOfWork
from src.domain.entities import UserAccount

__all__ = ["ProvisionUserOnFirstSignIn", "ProvisionResult"]


@dataclass(frozen=True, slots=True)
class ProvisionResult:
    user: UserAccount
    is_newly_created: bool


class ProvisionUserOnFirstSignIn:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        clock: Clock,
        super_admin_emails: frozenset[str],
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._super_admin_emails = super_admin_emails
        self._id_factory = id_factory

    async def execute(self, claims: ClerkClaims) -> ProvisionResult:
        async with self._uow:
            existing = await self._uow.users.get_by_clerk_id(claims.clerk_user_id)
            if existing is not None:
                # Refresh email on every sign-in (Clerk is the source of truth)
                # — but keep this minimal in v1; full sync would land in a
                # dedicated update use case.
                return ProvisionResult(user=existing, is_newly_created=False)
            user = UserAccount.provision(
                id=self._id_factory(),
                clerk_user_id=claims.clerk_user_id,
                email=claims.email,
                display_name=claims.display_name,
                super_admin_emails=self._super_admin_emails,
                now=self._clock.now(),
            )
            await self._uow.users.add(user)
            await self._uow.commit()
            return ProvisionResult(user=user, is_newly_created=True)
