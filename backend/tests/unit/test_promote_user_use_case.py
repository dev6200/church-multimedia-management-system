"""Unit test for ``PromoteUser`` (T124)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.role_management import PromoteUser
from src.domain.entities import UserAccount
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import ForbiddenError, NotFoundError
from src.domain.value_objects import Role
from tests.unit.fakes import FixedClock, InMemoryUnitOfWork


def _super_admin_actor() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        clerk_user_id="boss",
        email="boss@parish.example.org",
        role=Role.SUPER_ADMIN,
    )


def _seed(uow: InMemoryUnitOfWork, role: Role) -> UserAccount:
    user = UserAccount(
        id=uuid4(),
        clerk_user_id="target",
        email="target@parish.example.org",
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


async def test_promote_user_to_admin(uow: InMemoryUnitOfWork) -> None:
    target = _seed(uow, Role.USER)
    use_case = PromoteUser(uow=uow, clock=FixedClock())
    promoted = await use_case.execute(
        target.id, expected_version=target.version, actor=_super_admin_actor()
    )
    assert promoted.role is Role.ADMIN
    assert promoted.version == 2


async def test_promote_admin_is_noop(uow: InMemoryUnitOfWork) -> None:
    target = _seed(uow, Role.ADMIN)
    use_case = PromoteUser(uow=uow, clock=FixedClock())
    promoted = await use_case.execute(
        target.id, expected_version=target.version, actor=_super_admin_actor()
    )
    assert promoted.role is Role.ADMIN
    # No-op preserves version.
    assert promoted.version == 1


async def test_promote_requires_super_admin_actor(uow: InMemoryUnitOfWork) -> None:
    target = _seed(uow, Role.USER)
    not_super = CurrentUser(
        id=uuid4(),
        clerk_user_id="admin",
        email="admin@parish.example.org",
        role=Role.ADMIN,
    )
    use_case = PromoteUser(uow=uow, clock=FixedClock())
    with pytest.raises(ForbiddenError):
        await use_case.execute(
            target.id, expected_version=target.version, actor=not_super
        )


async def test_promote_unknown_user_raises_not_found(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = PromoteUser(uow=uow, clock=FixedClock())
    with pytest.raises(NotFoundError):
        await use_case.execute(
            uuid4(), expected_version=1, actor=_super_admin_actor()
        )
