"""Unit test for ``DeleteTaxonomyValueWithDetach`` (T105) — FR-019."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.taxonomy_value_management import (
    CreateTaxonomyValue,
    DeleteTaxonomyValueWithDetach,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import TaxonomyInUseError
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


async def test_delete_unused_value_succeeds(uow: InMemoryUnitOfWork) -> None:
    actor = _actor()
    seed = await CreateTaxonomyValue(uow=uow, clock=FixedClock()).execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=actor
    )
    detached = await DeleteTaxonomyValueWithDetach(uow=uow).execute(
        seed.id, detach=False, actor=actor
    )
    assert detached == 0
    assert seed.id not in uow.taxonomies.store


async def test_delete_in_use_value_without_detach_raises(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    seed = await CreateTaxonomyValue(uow=uow, clock=FixedClock()).execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=actor
    )
    uow.taxonomies.usage[seed.id] = 4

    with pytest.raises(TaxonomyInUseError) as exc:
        await DeleteTaxonomyValueWithDetach(uow=uow).execute(
            seed.id, detach=False, actor=actor
        )
    assert exc.value.usage_count == 4


async def test_delete_in_use_value_with_detach_returns_usage(
    uow: InMemoryUnitOfWork,
) -> None:
    actor = _actor()
    seed = await CreateTaxonomyValue(uow=uow, clock=FixedClock()).execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=actor
    )
    uow.taxonomies.usage[seed.id] = 7

    detached = await DeleteTaxonomyValueWithDetach(uow=uow).execute(
        seed.id, detach=True, actor=actor
    )
    assert detached == 7
    assert seed.id not in uow.taxonomies.store
