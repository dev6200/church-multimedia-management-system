"""Optional-field-definition management use cases (T116) — FR-018, FR-019."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

from src.application.ports import Clock, UnitOfWork
from src.domain.entities import OptionalFieldDefinition
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import (
    DuplicateOptionalFieldError,
    NotFoundError,
    TaxonomyInUseError,
)

__all__ = [
    "CreateOptionalField",
    "RenameOptionalField",
    "DeleteOptionalFieldWithDetach",
]


class CreateOptionalField:
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
        self, *, label: str, actor: CurrentUser
    ) -> OptionalFieldDefinition:
        async with self._uow:
            definition = OptionalFieldDefinition.create(
                id=self._id_factory(),
                label=label,
                actor_id=actor.id,
                now=self._clock.now(),
            )
            existing = await self._uow.optional_fields.find_by_norm(definition.label_norm)
            if existing is not None:
                raise DuplicateOptionalFieldError(
                    f"An optional field labelled '{label}' already exists",
                    existing_id=existing.id,
                )
            await self._uow.optional_fields.add(definition)
            await self._uow.commit()
            return definition


class RenameOptionalField:
    def __init__(self, *, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        definition_id: UUID,
        *,
        new_label: str,
        expected_version: int,
        actor: CurrentUser,
    ) -> OptionalFieldDefinition:
        async with self._uow:
            definition = await self._uow.optional_fields.get_by_id(definition_id)
            if definition is None:
                raise NotFoundError(
                    "Optional-field definition not found",
                    definition_id=str(definition_id),
                )
            new_norm = new_label.strip().lower()
            if new_norm != definition.label_norm:
                conflict = await self._uow.optional_fields.find_by_norm(new_norm)
                if conflict is not None and conflict.id != definition.id:
                    raise DuplicateOptionalFieldError(
                        f"An optional field labelled '{new_label}' already exists",
                        existing_id=conflict.id,
                    )
            definition.rename(
                new_label=new_label, actor_id=actor.id, now=self._clock.now()
            )
            await self._uow.optional_fields.rename_with_version(
                definition, expected_version=expected_version
            )
            await self._uow.commit()
            return definition


class DeleteOptionalFieldWithDetach:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        definition_id: UUID,
        *,
        detach: bool,
        actor: CurrentUser,
    ) -> int:
        async with self._uow:
            definition = await self._uow.optional_fields.get_by_id(definition_id)
            if definition is None:
                raise NotFoundError(
                    "Optional-field definition not found",
                    definition_id=str(definition_id),
                )
            usage = await self._uow.optional_fields.count_usage(definition_id)
            if usage > 0 and not detach:
                raise TaxonomyInUseError(
                    f"Optional field '{definition.label}' is used by {usage} song(s)",
                    usage_count=usage,
                )
            detached = await self._uow.optional_fields.delete_with_detach(
                definition_id, detach=detach
            )
            await self._uow.commit()
            return detached
