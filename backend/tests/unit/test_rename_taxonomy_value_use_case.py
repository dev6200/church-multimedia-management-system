"""Unit test for ``RenameTaxonomyValue`` (T104)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.taxonomy_value_management import (
    CreateTaxonomyValue,
    RenameTaxonomyValue,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import (
    DuplicateTaxonomyValueError,
    VersionConflictError,
)
from src.domain.value_objects import Role, TaxonomyKind
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


async def test_rename_updates_name_and_norm(uow: InMemoryUnitOfWork) -> None:
    actor = _actor()
    creator = CreateTaxonomyValue(uow=uow, clock=FixedClock())
    seed = await creator.execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=actor
    )

    rename = RenameTaxonomyValue(uow=uow, clock=FixedClock())
    renamed = await rename.execute(
        seed.id,
        new_name="Advent of the Lord",
        expected_version=seed.version,
        actor=actor,
    )
    assert renamed.name == "Advent of the Lord"
    assert renamed.name_norm == "advent of the lord"
    assert renamed.version == seed.version + 1


async def test_rename_into_existing_norm_raises_duplicate(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    creator = CreateTaxonomyValue(uow=uow, clock=FixedClock())
    a = await creator.execute(kind=TaxonomyKind.SEASON, name="Advent", actor=actor)
    b = await creator.execute(kind=TaxonomyKind.SEASON, name="Christmas", actor=actor)

    rename = RenameTaxonomyValue(uow=uow, clock=FixedClock())
    with pytest.raises(DuplicateTaxonomyValueError):
        await rename.execute(
            b.id,
            new_name="advent",  # collides with `a` (case-insensitive)
            expected_version=b.version,
            actor=actor,
        )


async def test_rename_with_stale_version_raises(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    seed = await CreateTaxonomyValue(uow=uow, clock=FixedClock()).execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=actor
    )
    rename = RenameTaxonomyValue(uow=uow, clock=FixedClock())
    with pytest.raises(VersionConflictError):
        await rename.execute(
            seed.id,
            new_name="Advent II",
            expected_version=seed.version + 99,
            actor=actor,
        )
