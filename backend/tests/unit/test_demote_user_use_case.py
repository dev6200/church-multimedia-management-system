"""Unit test for ``DemoteUser`` (T125) — FR-006 last-Super-Admin invariant."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.role_management import DemoteUser
from src.domain.entities import UserAccount
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import LastSuperAdminError
from src.domain.value_objects import Role
from tests.unit.fakes import FixedClock, InMemoryUnitOfWork


def _super_admin_actor() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        clerk_user_id="boss",
        email="boss@parish.example.org",
        role=Role.SUPER_ADMIN,
    )


def _seed(uow: InMemoryUnitOfWork, role: Role, *, clerk_id: str) -> UserAccount:
    user = UserAccount(
        id=uuid4(),
        clerk_user_id=clerk_id,
        email=f"{clerk_id}@parish.example.org",
        display_name=None,
        role=role,
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        version=1,
    )
    uow.users.store[user.id] = user
    return user


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


async def test_demote_admin_to_user(uow: InMemoryUnitOfWork) -> None:
    target = _seed(uow, Role.ADMIN, clerk_id="bob")
    use_case = DemoteUser(uow=uow, clock=FixedClock())
    demoted = await use_case.execute(
        target.id, expected_version=target.version, actor=_super_admin_actor()
    )
    assert demoted.role is Role.USER


async def test_demote_last_super_admin_raises(uow: InMemoryUnitOfWork) -> None:
    target = _seed(uow, Role.SUPER_ADMIN, clerk_id="lonely_boss")
    use_case = DemoteUser(uow=uow, clock=FixedClock())
    with pytest.raises(LastSuperAdminError):
        await use_case.execute(
            target.id, expected_version=target.version, actor=_super_admin_actor()
        )


async def test_demote_super_admin_when_another_remains(
    uow: InMemoryUnitOfWork,
) -> None:
    _seed(uow, Role.SUPER_ADMIN, clerk_id="other_boss")
    target = _seed(uow, Role.SUPER_ADMIN, clerk_id="boss_to_demote")
    use_case = DemoteUser(uow=uow, clock=FixedClock())
    demoted = await use_case.execute(
        target.id, expected_version=target.version, actor=_super_admin_actor()
    )
    assert demoted.role is Role.USER
