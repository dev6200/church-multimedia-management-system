"""Role-management use cases (T132) — FR-005, FR-006."""

from __future__ import annotations

from uuid import UUID

from src.application.ports import Clock, UnitOfWork
from src.domain.entities import UserAccount
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import ForbiddenError, LastSuperAdminError, NotFoundError
from src.domain.value_objects import Role

__all__ = ["PromoteUser", "DemoteUser"]


class PromoteUser:
    """USER → ADMIN. The Super Admin promotion is intentionally NOT exposed
    via the API in v1 (data-model.md §1)."""

    def __init__(self, *, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self, target_id: UUID, *, expected_version: int, actor: CurrentUser
    ) -> UserAccount:
        if actor.role is not Role.SUPER_ADMIN:
            raise ForbiddenError("Only Super Admins may promote users")
        async with self._uow:
            target = await self._uow.users.get_by_id(target_id)
            if target is None:
                raise NotFoundError("User not found", user_id=str(target_id))
            target.promote_to_admin(now=self._clock.now())
            await self._uow.users.update_role_with_version(
                target, expected_version=expected_version
            )
            await self._uow.commit()
            return target


class DemoteUser:
    """ADMIN → USER. SUPER_ADMIN demotion is rejected unless another Super
    Admin remains (FR-006)."""

    def __init__(self, *, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self, target_id: UUID, *, expected_version: int, actor: CurrentUser
    ) -> UserAccount:
        if actor.role is not Role.SUPER_ADMIN:
            raise ForbiddenError("Only Super Admins may demote users")
        async with self._uow:
            target = await self._uow.users.get_by_id(target_id)
            if target is None:
                raise NotFoundError("User not found", user_id=str(target_id))
            if target.role is Role.SUPER_ADMIN:
                # Compute the count *after* this demotion would land.
                current_super_admins = await self._uow.users.count_by_role(
                    Role.SUPER_ADMIN
                )
                target.demote_to_user(
                    now=self._clock.now(),
                    remaining_super_admin_count_after=current_super_admins - 1,
                )
            else:
                target.demote_to_user(now=self._clock.now())
            await self._uow.users.update_role_with_version(
                target, expected_version=expected_version
            )
            await self._uow.commit()
            return target


# Wider FR-006 invariant: even without a SUPER_ADMIN demotion, the API may
# never accept an `update_role_with_version` that would leave zero Super
# Admins. PromoteUser is restricted to USER↔ADMIN so it's safe; DemoteUser
# enforces the count check above. The OpenAPI contract restricts the body's
# ``role`` enum to {USER, ADMIN}, so PUT /super-admin/users/{id}/role can't
# be used to demote a SUPER_ADMIN at all (the v1 design seeds Super Admins
# only via env allowlist on first sign-in).
