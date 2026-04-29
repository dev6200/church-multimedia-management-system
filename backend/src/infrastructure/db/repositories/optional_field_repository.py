"""SQLAlchemy implementation of ``OptionalFieldRepository``.

``list_all`` lands here (T065 — US1). Admin write methods (T114 — US3).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import OptionalFieldDefinition, OptionalFieldKind
from src.domain.errors import TaxonomyInUseError, VersionConflictError
from src.domain.repositories import OptionalFieldRepository
from src.infrastructure.db.models import (
    OptionalFieldDefinitionModel,
    SongOptionalFieldValueModel,
)

__all__ = ["SqlAlchemyOptionalFieldRepository"]


def _row_to_entity(row: OptionalFieldDefinitionModel) -> OptionalFieldDefinition:
    return OptionalFieldDefinition(
        id=row.id,
        label=row.label,
        label_norm=row.label_norm,
        kind=OptionalFieldKind(row.kind),
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
        version=row.version,
    )


class SqlAlchemyOptionalFieldRepository(OptionalFieldRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, definition_id: UUID) -> OptionalFieldDefinition | None:
        row = await self._session.get(OptionalFieldDefinitionModel, definition_id)
        return _row_to_entity(row) if row else None

    async def list_all(self) -> list[OptionalFieldDefinition]:
        stmt = select(OptionalFieldDefinitionModel).order_by(
            OptionalFieldDefinitionModel.label
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_entity(r) for r in rows]

    async def find_by_norm(self, label_norm: str) -> OptionalFieldDefinition | None:
        stmt = select(OptionalFieldDefinitionModel).where(
            OptionalFieldDefinitionModel.label_norm == label_norm
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_entity(row) if row else None

    async def add(self, definition: OptionalFieldDefinition) -> None:
        self._session.add(
            OptionalFieldDefinitionModel(
                id=definition.id,
                label=definition.label,
                label_norm=definition.label_norm,
                kind=definition.kind.value,
                created_at=definition.created_at,
                updated_at=definition.updated_at,
                created_by=definition.created_by,
                updated_by=definition.updated_by,
                version=definition.version,
            )
        )
        await self._session.flush()

    async def rename_with_version(
        self, definition: OptionalFieldDefinition, *, expected_version: int
    ) -> None:
        result = await self._session.execute(
            update(OptionalFieldDefinitionModel)
            .where(
                OptionalFieldDefinitionModel.id == definition.id,
                OptionalFieldDefinitionModel.version == expected_version,
            )
            .values(
                label=definition.label,
                label_norm=definition.label_norm,
                updated_at=definition.updated_at,
                updated_by=definition.updated_by,
                version=definition.version,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise VersionConflictError(expected_version=expected_version)

    async def count_usage(self, definition_id: UUID) -> int:
        stmt = select(func.count()).select_from(SongOptionalFieldValueModel).where(
            SongOptionalFieldValueModel.definition_id == definition_id
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def delete_with_detach(self, definition_id: UUID, *, detach: bool) -> int:
        usage = await self.count_usage(definition_id)
        if usage > 0 and not detach:
            raise TaxonomyInUseError(
                f"Optional-field definition in use by {usage} song(s)",
                usage_count=usage,
            )
        await self._session.execute(
            delete(SongOptionalFieldValueModel).where(
                SongOptionalFieldValueModel.definition_id == definition_id
            )
        )
        await self._session.execute(
            delete(OptionalFieldDefinitionModel).where(
                OptionalFieldDefinitionModel.id == definition_id
            )
        )
        return usage
