"""Taxonomies router.

Read endpoints are anonymous-readable (FR-031). Admin write endpoints (T117)
are role-gated.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.application.ports import Clock, UnitOfWork
from src.application.use_cases.taxonomy_value_management import (
    CreateTaxonomyValue,
    DeleteTaxonomyValueWithDetach,
    RenameTaxonomyValue,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.value_objects import Role, TaxonomyKind
from src.interfaces.api.deps import get_clock, get_uow, require_role
from src.interfaces.api.schemas.common import TaxonomyValueSchema

router = APIRouter(prefix="/api/v1/admin/taxonomies", tags=["taxonomies"])


_KIND_SLUG_TO_ENUM: dict[str, TaxonomyKind] = {
    "seasons": TaxonomyKind.SEASON,
    "masses": TaxonomyKind.MASS,
    "special_events": TaxonomyKind.SPECIAL_EVENT,
}


def _resolve_kind(slug: str) -> TaxonomyKind:
    kind = _KIND_SLUG_TO_ENUM.get(slug)
    if kind is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Unknown taxonomy '{slug}'"},
        )
    return kind


def _parse_if_match(if_match: str | None) -> int:
    if if_match is None or not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "Mutating taxonomy values requires the current version in If-Match",
            },
        )
    cleaned = if_match.strip().strip('"')
    try:
        return int(cleaned)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "validation_error",
                "message": "If-Match must be an integer version",
            },
        ) from exc


def _value_to_schema(v) -> TaxonomyValueSchema:
    return TaxonomyValueSchema(
        id=v.id,
        kind=v.kind.value,
        name=v.name,
        version=v.version,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


class TaxonomyValueWriteSchema(BaseModel):
    name: str = Field(min_length=1, max_length=80)


# ----------------------------------------------------------------- read (FR-031)


@router.get("/{kind}", response_model=list[TaxonomyValueSchema])
async def list_taxonomy_values(
    kind: str,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> list[TaxonomyValueSchema]:
    enum_kind = _resolve_kind(kind)
    async with uow:
        values = await uow.taxonomies.list_by_kind(enum_kind)
    return [_value_to_schema(v) for v in values]


# ----------------------------------------------------------------- admin (T117)


@router.post(
    "/{kind}",
    response_model=TaxonomyValueSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_taxonomy_value(
    kind: str,
    body: TaxonomyValueWriteSchema,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> TaxonomyValueSchema:
    enum_kind = _resolve_kind(kind)
    use_case = CreateTaxonomyValue(uow=uow, clock=clock)
    value = await use_case.execute(kind=enum_kind, name=body.name, actor=actor)
    return _value_to_schema(value)


@router.put("/{kind}/{value_id}", response_model=TaxonomyValueSchema)
async def rename_taxonomy_value(
    kind: str,
    value_id: UUID,
    body: TaxonomyValueWriteSchema,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> TaxonomyValueSchema:
    _resolve_kind(kind)  # 404 on unknown slug; the use case ignores `kind` since it's keyed by id
    expected_version = _parse_if_match(if_match)
    use_case = RenameTaxonomyValue(uow=uow, clock=clock)
    value = await use_case.execute(
        value_id,
        new_name=body.name,
        expected_version=expected_version,
        actor=actor,
    )
    return _value_to_schema(value)


@router.delete("/{kind}/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_taxonomy_value(
    kind: str,
    value_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    detach: bool = False,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    _resolve_kind(kind)
    _parse_if_match(if_match)  # value-version isn't used by delete; we still
    # require the header per the OpenAPI contract for parity with PUT.
    use_case = DeleteTaxonomyValueWithDetach(uow=uow)
    await use_case.execute(value_id, detach=detach, actor=actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{kind}/{value_id}/usage")
async def taxonomy_value_usage(
    kind: str,
    value_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> dict[str, int]:
    _resolve_kind(kind)
    async with uow:
        count = await uow.taxonomies.count_usage(value_id)
    return {"usage_count": count}
