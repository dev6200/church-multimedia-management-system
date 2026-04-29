"""SQLAlchemy implementation of ``TaxonomyRepository``.

Read-side ``list_by_kind`` lands in T064 (US1). Admin write methods land
here as part of T113 (US3).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import TaxonomyValue
from src.domain.errors import TaxonomyInUseError, VersionConflictError
from src.domain.repositories import TaxonomyRepository
from src.domain.value_objects import TaxonomyKind
from src.infrastructure.db.models import (
    SongTaxonomyValueLink,
    TaxonomyValueModel,
)

__all__ = ["SqlAlchemyTaxonomyRepository"]


def _row_to_entity(row: TaxonomyValueModel) -> TaxonomyValue:
    return TaxonomyValue(
        id=row.id,
        kind=TaxonomyKind(row.kind),
        name=row.name,
        name_norm=row.name_norm,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
        version=row.version,
    )


class SqlAlchemyTaxonomyRepository(TaxonomyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, value_id: UUID) -> TaxonomyValue | None:
        row = await self._session.get(TaxonomyValueModel, value_id)
        return _row_to_entity(row) if row else None

    async def list_by_kind(self, kind: TaxonomyKind) -> list[TaxonomyValue]:
        stmt = (
            select(TaxonomyValueModel)
            .where(TaxonomyValueModel.kind == kind.value)
            .order_by(TaxonomyValueModel.name)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_entity(r) for r in rows]

    async def find_by_kind_and_norm(
        self, kind: TaxonomyKind, name_norm: str
    ) -> TaxonomyValue | None:
        stmt = select(TaxonomyValueModel).where(
            TaxonomyValueModel.kind == kind.value,
            TaxonomyValueModel.name_norm == name_norm,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_entity(row) if row else None

    async def add(self, value: TaxonomyValue) -> None:
        self._session.add(
            TaxonomyValueModel(
                id=value.id,
                kind=value.kind.value,
                name=value.name,
                name_norm=value.name_norm,
                created_at=value.created_at,
                updated_at=value.updated_at,
                created_by=value.created_by,
                updated_by=value.updated_by,
                version=value.version,
            )
        )
        await self._session.flush()

    async def rename_with_version(
        self, value: TaxonomyValue, *, expected_version: int
    ) -> None:
        result = await self._session.execute(
            update(TaxonomyValueModel)
            .where(
                TaxonomyValueModel.id == value.id,
                TaxonomyValueModel.version == expected_version,
            )
            .values(
                name=value.name,
                name_norm=value.name_norm,
                updated_at=value.updated_at,
                updated_by=value.updated_by,
                version=value.version,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise VersionConflictError(expected_version=expected_version)

    async def count_usage(self, value_id: UUID) -> int:
        stmt = select(func.count()).select_from(SongTaxonomyValueLink).where(
            SongTaxonomyValueLink.taxonomy_value_id == value_id
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def delete_with_detach(self, value_id: UUID, *, detach: bool) -> int:
        usage = await self.count_usage(value_id)
        if usage > 0 and not detach:
            raise TaxonomyInUseError(
                f"Taxonomy value in use by {usage} song(s)", usage_count=usage
            )
        # Atomic detach + delete inside the caller's transaction.
        await self._session.execute(
            delete(SongTaxonomyValueLink).where(
                SongTaxonomyValueLink.taxonomy_value_id == value_id
            )
        )
        await self._session.execute(
            delete(TaxonomyValueModel).where(TaxonomyValueModel.id == value_id)
        )
        return usage
