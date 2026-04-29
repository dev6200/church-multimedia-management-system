"""CreateSong use case (T093) — FR-008, FR-009, FR-014, FR-016, FR-032."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.ports import Clock, UnitOfWork
from src.domain.entities import Composer, Song, SongOptionalLink
from src.domain.entities.user_account import CurrentUser
from src.domain.errors import DuplicateSongError
from src.domain.value_objects import ComposerName, LinkUrl

__all__ = ["CreateSong", "CreateSongInput", "OptionalLinkInput"]


@dataclass(frozen=True, slots=True)
class OptionalLinkInput:
    definition_id: UUID
    value_url: str


@dataclass(frozen=True, slots=True)
class CreateSongInput:
    title: str
    composer_names: tuple[str, ...]
    season_ids: frozenset[UUID]
    mass_ids: frozenset[UUID]
    special_event_ids: frozenset[UUID]
    optional_links: tuple[OptionalLinkInput, ...]


class CreateSong:
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
        self, input: CreateSongInput, *, actor: CurrentUser
    ) -> Song:
        now = self._clock.now()
        # Validate URLs eagerly so we never persist malformed values.
        validated_links: tuple[SongOptionalLink, ...] = tuple(
            SongOptionalLink(
                definition_id=link.definition_id,
                value=LinkUrl.parse(link.value_url),
            )
            for link in input.optional_links
        )

        async with self._uow:
            composers = await self._find_or_create_composers(input.composer_names, now=now)
            taxonomy_ids = (
                input.season_ids | input.mass_ids | input.special_event_ids
            )
            song = Song.create(
                id=self._id_factory(),
                title=input.title,
                composers=composers,
                taxonomy_value_ids=frozenset(taxonomy_ids),
                optional_links=validated_links,
                actor_id=actor.id,
                now=now,
            )
            # Pre-flight conflict check (the repo's UNIQUE will catch races too).
            existing = await self._uow.songs.find_by_dedup_key(song.dedup_key)
            if existing is not None:
                raise DuplicateSongError(
                    "A song with the same title and composer set already exists",
                    conflicting_song_id=existing.id,
                )
            await self._uow.songs.add(song, composers=composers)
            await self._uow.commit()
            return song

    async def _find_or_create_composers(
        self, raw_names: tuple[str, ...], *, now
    ) -> list[Composer]:
        # Deduplicate by normalised name so duplicates in input don't create
        # two associations to the same composer.
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
            composer = Composer.from_name(
                id=self._id_factory(), name=name, now=now
            )
            composers.append(composer)
        return composers
