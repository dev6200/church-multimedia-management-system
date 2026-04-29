"""Unit test for ``DeleteOptionalFieldWithDetach`` (T106)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.optional_field_management import (
    CreateOptionalField,
    DeleteOptionalFieldWithDetach,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import TaxonomyInUseError
from src.domain.value_objects import Role
from tests.unit.fakes import FixedClock, InMemoryUnitOfWork


def _actor() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        clerk_user_id="admin",
        email="admin@parish.example.org",
        role=Role.ADMIN,
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


async def test_delete_unused_definition_succeeds(uow: InMemoryUnitOfWork) -> None:
    actor = _actor()
    seed = await CreateOptionalField(uow=uow, clock=FixedClock()).execute(
        label="PowerPoint link", actor=actor
    )
    await DeleteOptionalFieldWithDetach(uow=uow).execute(
        seed.id, detach=False, actor=actor
    )
    assert seed.id not in uow.optional_fields.store


async def test_delete_in_use_without_detach_raises(uow: InMemoryUnitOfWork) -> None:
    actor = _actor()
    seed = await CreateOptionalField(uow=uow, clock=FixedClock()).execute(
        label="PowerPoint link", actor=actor
    )
    uow.optional_fields.usage[seed.id] = 3
    with pytest.raises(TaxonomyInUseError):
        await DeleteOptionalFieldWithDetach(uow=uow).execute(
            seed.id, detach=False, actor=actor
        )
