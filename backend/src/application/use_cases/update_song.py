"""UpdateSong use case (T094) — FR-011, FR-016, FR-030."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.ports import Clock, UnitOfWork
from src.application.use_cases.create_song import CreateSongInput, OptionalLinkInput
from src.domain.entities import Composer, Song, SongOptionalLink
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateSongError, NotFoundError
from src.domain.value_objects import ComposerName, LinkUrl

__all__ = ["UpdateSong", "UpdateSongInput"]


@dataclass(frozen=True, slots=True)
class UpdateSongInput:
    title: str
    composer_names: tuple[str, ...]
    season_ids: frozenset[UUID]
    mass_ids: frozenset[UUID]
    special_event_ids: frozenset[UUID]
    optional_links: tuple[OptionalLinkInput, ...]
    expected_version: int


class UpdateSong:
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
        self,
        song_id: UUID,
        input: UpdateSongInput,
        *,
        actor: CurrentUser,
    ) -> Song:
        now = self._clock.now()
        validated_links: tuple[SongOptionalLink, ...] = tuple(
            SongOptionalLink(
                definition_id=link.definition_id,
                value=LinkUrl.parse(link.value_url),
            )
            for link in input.optional_links
        )

        async with self._uow:
            song = await self._uow.songs.get_by_id(song_id)
            if song is None:
                raise NotFoundError("Song not found", song_id=str(song_id))

            composers = await self._find_or_create_composers(input.composer_names, now=now)
            taxonomy_ids = (
                input.season_ids | input.mass_ids | input.special_event_ids
            )
            song.update(
                title=input.title,
                composers=composers,
                taxonomy_value_ids=frozenset(taxonomy_ids),
                optional_links=validated_links,
                actor_id=actor.id,
                now=now,
            )
            # Pre-flight conflict check against OTHER songs.
            existing = await self._uow.songs.find_by_dedup_key(song.dedup_key)
            if existing is not None and existing.id != song.id:
                raise DuplicateSongError(
                    "A song with the same title and composer set already exists",
                    conflicting_song_id=existing.id,
                )
            await self._uow.songs.update_with_version(
                song,
                composers=composers,
                expected_version=input.expected_version,
            )
            await self._uow.commit()
            return song

    async def _find_or_create_composers(
        self, raw_names: tuple[str, ...], *, now
    ) -> list[Composer]:
        seen: dict[str, ComposerName] = {}
        for raw in raw_names:
            parsed = ComposerName.parse(raw)
            seen.setdefault(parsed.norm, parsed)
        composers: list[Composer] = []
        for name in seen.values():
            existing = await self._uow.songs.find_composer_by_norm(name.norm)
            if existing is not None:
                composers.append(existing)
                continue
            composers.append(Composer.from_name(id=self._id_factory(), name=name, now=now))
        return composers
