"""SQLAlchemy implementation of ``UserRepository``.

Phase 2 covered the provisioning path (``add``, ``get_by_clerk_id``,
``get_by_id``). Phase 6 (T131) adds ``list_paginated``, ``count_by_role``, and
``update_role_with_version`` for Super Admin role management.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import UserAccount
from src.domain.errors import VersionConflictError
from src.domain.repositories import UserPage, UserRepository
from src.domain.value_objects import Role
from src.infrastructure.db.models import UserAccountModel

__all__ = ["SqlAlchemyUserRepository"]


def _row_to_entity(row: UserAccountModel) -> UserAccount:
    return UserAccount(
        id=row.id,
        clerk_user_id=row.clerk_user_id,
        email=row.email,
        display_name=row.display_name,
        role=Role(row.role),
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> UserAccount | None:
        row = await self._session.get(UserAccountModel, user_id)
        return _row_to_entity(row) if row else None

    async def get_by_clerk_id(self, clerk_user_id: str) -> UserAccount | None:
        stmt = select(UserAccountModel).where(
            UserAccountModel.clerk_user_id == clerk_user_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_entity(row) if row else None

    async def add(self, user: UserAccount) -> None:
        self._session.add(
            UserAccountModel(
                id=user.id,
                clerk_user_id=user.clerk_user_id,
                email=user.email,
                display_name=user.display_name,
                role=user.role.value,
                created_at=user.created_at,
                updated_at=user.updated_at,
                version=user.version,
            )
        )
        await self._session.flush()

    async def list_paginated(
        self, *, page: int, page_size: int, q: str | None = None
    ) -> UserPage:
        base = select(UserAccountModel)
        if q:
            term = f"%{q.strip().lower()}%"
            base = base.where(
                or_(
                    func.lower(UserAccountModel.email).like(term),
                    func.lower(UserAccountModel.display_name).like(term),
                )
            )
        total = (
            await self._session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = (
            base.order_by(UserAccountModel.email)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return UserPage(
            items=[_row_to_entity(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def count_by_role(self, role: Role) -> int:
        stmt = select(func.count()).select_from(UserAccountModel).where(
            UserAccountModel.role == role.value
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def update_role_with_version(
        self, user: UserAccount, *, expected_version: int
    ) -> None:
        result = await self._session.execute(
            update(UserAccountModel)
            .where(
                UserAccountModel.id == user.id,
                UserAccountModel.version == expected_version,
            )
            .values(
                role=user.role.value,
                updated_at=user.updated_at,
                version=user.version,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise VersionConflictError(expected_version=expected_version)
