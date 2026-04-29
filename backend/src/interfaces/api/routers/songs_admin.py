"""Admin / Super-Admin write endpoints for songs (T097).

- ``POST /api/v1/admin/songs`` — create
- ``PUT  /api/v1/songs/{id}`` — update (under public path; admin-gated)
- ``DELETE /api/v1/songs/{id}`` — delete (under public path; admin-gated)

Each mutating endpoint requires ``If-Match`` per FR-030 except for create.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from src.application.ports import Clock, UnitOfWork
from src.application.use_cases.create_song import (
    CreateSong,
    CreateSongInput,
    OptionalLinkInput,
)
from src.application.use_cases.delete_song import DeleteSong
from src.application.use_cases.update_song import UpdateSong, UpdateSongInput
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import NotFoundError
from src.domain.value_objects import Role
from src.interfaces.api.deps import get_clock, get_uow, require_role
from src.interfaces.api.routers.songs_public import _detail_to_schema
from src.interfaces.api.schemas.songs import (
    SongDetailSchema,
    SongWriteRequestSchema,
)
from src.application.use_cases.get_song import GetSong

router_admin_create = APIRouter(prefix="/api/v1/admin/songs", tags=["catalog-admin"])
router_admin_mutate = APIRouter(prefix="/api/v1/songs", tags=["catalog-admin"])


def _to_create_input(body: SongWriteRequestSchema) -> CreateSongInput:
    return CreateSongInput(
        title=body.title,
        composer_names=tuple(c.name for c in body.composers),
        season_ids=frozenset(body.season_ids),
        mass_ids=frozenset(body.mass_ids),
        special_event_ids=frozenset(body.special_event_ids),
        optional_links=tuple(
            OptionalLinkInput(definition_id=l.definition_id, value_url=l.value_url)
            for l in body.optional_fields
        ),
    )


def _to_update_input(body: SongWriteRequestSchema, *, expected_version: int) -> UpdateSongInput:
    return UpdateSongInput(
        title=body.title,
        composer_names=tuple(c.name for c in body.composers),
        season_ids=frozenset(body.season_ids),
        mass_ids=frozenset(body.mass_ids),
        special_event_ids=frozenset(body.special_event_ids),
        optional_links=tuple(
            OptionalLinkInput(definition_id=l.definition_id, value_url=l.value_url)
            for l in body.optional_fields
        ),
        expected_version=expected_version,
    )


def _parse_if_match(if_match: str | None) -> int:
    if if_match is None or not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "Mutating songs requires the current version in If-Match",
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


@router_admin_create.post(
    "",
    response_model=SongDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_song(
    body: SongWriteRequestSchema,
    response: Response,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SongDetailSchema:
    use_case = CreateSong(uow=uow, clock=clock)
    song = await use_case.execute(_to_create_input(body), actor=actor)
    response.headers["Location"] = f"/api/v1/songs/{song.id}"
    # Return the detail view via GetSong so we hydrate composers/taxonomies.
    detail = await GetSong(uow=uow).execute(song.id)
    return _detail_to_schema(detail)


@router_admin_mutate.put("/{song_id}", response_model=SongDetailSchema)
async def update_song(
    song_id: UUID,
    body: SongWriteRequestSchema,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> SongDetailSchema:
    expected_version = _parse_if_match(if_match)
    use_case = UpdateSong(uow=uow, clock=clock)
    song = await use_case.execute(
        song_id,
        _to_update_input(body, expected_version=expected_version),
        actor=actor,
    )
    detail = await GetSong(uow=uow).execute(song.id)
    return _detail_to_schema(detail)


@router_admin_mutate.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    song_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    ],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    expected_version = _parse_if_match(if_match)
    use_case = DeleteSong(uow=uow)
    try:
        await use_case.execute(song_id, expected_version=expected_version)
    except NotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
