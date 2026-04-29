"""Unit test for ``RenameOptionalField`` (T107) — FR-018: rename preserves
existing per-song values."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.optional_field_management import (
    CreateOptionalField,
    RenameOptionalField,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateOptionalFieldError
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


async def test_rename_updates_label_and_norm(uow: InMemoryUnitOfWork) -> None:
    actor = _actor()
    seed = await CreateOptionalField(uow=uow, clock=FixedClock()).execute(
        label="PowerPoint link", actor=actor
    )
    renamed = await RenameOptionalField(uow=uow, clock=FixedClock()).execute(
        seed.id,
        new_label="Slides link",
        expected_version=seed.version,
        actor=actor,
    )
    assert renamed.label == "Slides link"
    assert renamed.label_norm == "slides link"


async def test_rename_into_existing_label_raises_duplicate(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    creator = CreateOptionalField(uow=uow, clock=FixedClock())
    a = await creator.execute(label="PowerPoint link", actor=actor)
    b = await creator.execute(label="Sheet Music", actor=actor)
    with pytest.raises(DuplicateOptionalFieldError):
        await RenameOptionalField(uow=uow, clock=FixedClock()).execute(
            b.id,
            new_label="powerpoint link",
            expected_version=b.version,
            actor=actor,
        )
