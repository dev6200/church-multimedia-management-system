"""Unit test for ``CreateTaxonomyValue`` (T103)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.taxonomy_value_management import CreateTaxonomyValue
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateTaxonomyValueError
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


async def test_create_taxonomy_value_persists(uow: InMemoryUnitOfWork) -> None:
    use_case = CreateTaxonomyValue(uow=uow, clock=FixedClock())
    value = await use_case.execute(
        kind=TaxonomyKind.SEASON, name="Advent", actor=_actor()
    )
    assert value.kind is TaxonomyKind.SEASON
    assert value.name == "Advent"
    assert uow.taxonomies.store[value.id] is value


async def test_create_taxonomy_value_rejects_duplicate_within_kind(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateTaxonomyValue(uow=uow, clock=FixedClock())
    actor = _actor()
    await use_case.execute(kind=TaxonomyKind.SEASON, name="Advent", actor=actor)
    with pytest.raises(DuplicateTaxonomyValueError):
        await use_case.execute(
            kind=TaxonomyKind.SEASON, name="advent", actor=actor
        )


async def test_create_taxonomy_value_allows_same_name_in_different_kind(
    uow: InMemoryUnitOfWork,
) -> None:
    use_case = CreateTaxonomyValue(uow=uow, clock=FixedClock())
    actor = _actor()
    await use_case.execute(kind=TaxonomyKind.SEASON, name="Christmas", actor=actor)
    # Same display name in a different kind is allowed by data-model.md §4.
    other = await use_case.execute(
        kind=TaxonomyKind.SPECIAL_EVENT, name="Christmas", actor=actor
    )
    assert other.kind is TaxonomyKind.SPECIAL_EVENT
