"""Optional-field definitions router.

Read endpoint is anonymous-readable (FR-031). Admin write endpoints (T118)
are role-gated.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.application.ports import Clock, UnitOfWork
from src.application.use_cases.optional_field_management import (
    CreateOptionalField,
    DeleteOptionalFieldWithDetach,
    RenameOptionalField,
)
from src.domain.entities.user_account import CurrentUser
from src.domain.value_objects import Role
from src.interfaces.api.deps import get_clock, get_uow, require_role
from src.interfaces.api.schemas.common import OptionalFieldDefinitionSchema

router = APIRouter(prefix="/api/v1/admin/optional-fields", tags=["optional-fields"])


def _definition_to_schema(d) -> OptionalFieldDefinitionSchema:
    return OptionalFieldDefinitionSchema(
        id=d.id,
        label=d.label,
        kind=d.kind.value,
        version=d.version,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _parse_if_match(if_match: str | None) -> int:
    if if_match is None or not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "Mutating optional-field definitions requires the current version in If-Match",
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


class OptionalFieldWriteSchema(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    kind: str = "LINK"


# ----------------------------------------------------------------- read (FR-031)


@router.get("", response_model=list[OptionalFieldDefinitionSchema])
async def list_optional_fields(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> list[OptionalFieldDefinitionSchema]:
    async with uow:
        definitions = await uow.optional_fields.list_all()
    return [_definition_to_schema(d) for d in definitions]


# ----------------------------------------------------------------- admin (T118)


@router.post(
    "",
    response_model=OptionalFieldDefinitionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_optional_field(
    body: OptionalFieldWriteSchema,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> OptionalFieldDefinitionSchema:
    use_case = CreateOptionalField(uow=uow, clock=clock)
    definition = await use_case.execute(label=body.label, actor=actor)
    return _definition_to_schema(definition)


@router.put("/{definition_id}", response_model=OptionalFieldDefinitionSchema)
async def rename_optional_field(
    definition_id: UUID,
    body: OptionalFieldWriteSchema,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> OptionalFieldDefinitionSchema:
    expected_version = _parse_if_match(if_match)
    use_case = RenameOptionalField(uow=uow, clock=clock)
    definition = await use_case.execute(
        definition_id,
        new_label=body.label,
        expected_version=expected_version,
        actor=actor,
    )
    return _definition_to_schema(definition)


@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_optional_field(
    definition_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    detach: bool = False,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    _parse_if_match(if_match)
    use_case = DeleteOptionalFieldWithDetach(uow=uow)
    await use_case.execute(definition_id, detach=detach, actor=actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{definition_id}/usage")
async def optional_field_usage(
    definition_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> dict[str, int]:
    async with uow:
        count = await uow.optional_fields.count_usage(definition_id)
    return {"usage_count": count}
