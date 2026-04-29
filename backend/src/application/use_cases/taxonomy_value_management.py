"""Taxonomy-value management use cases (T115) — FR-017, FR-019.

- ``CreateTaxonomyValue`` — admin adds a new value to a taxonomy.
- ``RenameTaxonomyValue`` — admin renames an existing value.
- ``DeleteTaxonomyValueWithDetach`` — admin removes a value, optionally
  detaching it from songs that still reference it.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

from src.application.ports import Clock, UnitOfWork
from src.domain.entities import TaxonomyValue
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import (
    DuplicateTaxonomyValueError,
    NotFoundError,
    TaxonomyInUseError,
)
from src.domain.value_objects import TaxonomyKind

__all__ = [
    "CreateTaxonomyValue",
    "RenameTaxonomyValue",
    "DeleteTaxonomyValueWithDetach",
]


class CreateTaxonomyValue:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        clock: Clock,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_factory = id_factory

    async def execute(
        self, *, kind: TaxonomyKind, name: str, actor: CurrentUser
    ) -> TaxonomyValue:
        async with self._uow:
            value = TaxonomyValue.create(
                id=self._id_factory(),
                kind=kind,
                name=name,
                actor_id=actor.id,
                now=self._clock.now(),
            )
            existing = await self._uow.taxonomies.find_by_kind_and_norm(
                kind, value.name_norm
            )
            if existing is not None:
                raise DuplicateTaxonomyValueError(
                    f"A {kind.value} named '{name}' already exists",
                    existing_id=existing.id,
                )
            await self._uow.taxonomies.add(value)
            await self._uow.commit()
            return value


class RenameTaxonomyValue:
    def __init__(self, *, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        value_id: UUID,
        *,
        new_name: str,
        expected_version: int,
        actor: CurrentUser,
    ) -> TaxonomyValue:
        async with self._uow:
            value = await self._uow.taxonomies.get_by_id(value_id)
            if value is None:
                raise NotFoundError("Taxonomy value not found", value_id=str(value_id))
            new_norm = new_name.strip().lower()
            if new_norm != value.name_norm:
                conflict = await self._uow.taxonomies.find_by_kind_and_norm(
                    value.kind, new_norm
                )
                if conflict is not None and conflict.id != value.id:
                    raise DuplicateTaxonomyValueError(
                        f"A {value.kind.value} named '{new_name}' already exists",
                        existing_id=conflict.id,
                    )
            value.rename(new_name=new_name, actor_id=actor.id, now=self._clock.now())
            await self._uow.taxonomies.rename_with_version(
                value, expected_version=expected_version
            )
            await self._uow.commit()
            return value


class DeleteTaxonomyValueWithDetach:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        value_id: UUID,
        *,
        detach: bool,
        actor: CurrentUser,
    ) -> int:
        """Returns the number of detached associations (0 if not in use)."""

        async with self._uow:
            value = await self._uow.taxonomies.get_by_id(value_id)
            if value is None:
                raise NotFoundError("Taxonomy value not found", value_id=str(value_id))
            usage = await self._uow.taxonomies.count_usage(value_id)
            if usage > 0 and not detach:
                raise TaxonomyInUseError(
                    f"{value.kind.value} '{value.name}' is used by {usage} song(s)",
                    usage_count=usage,
                )
            detached = await self._uow.taxonomies.delete_with_detach(
                value_id, detach=detach
            )
            await self._uow.commit()
            return detached
