"""Domain repository ABCs.

Use cases depend on these; concrete implementations live in
``src/infrastructure/db/repositories/``. In-memory fakes satisfying these
interfaces live next to the unit tests.
"""

from src.domain.repositories.optional_field_repository import OptionalFieldRepository
from src.domain.repositories.song_repository import (
    Pagination,
    SongFilters,
    SongPage,
    SongRepository,
)
from src.domain.repositories.taxonomy_repository import TaxonomyRepository
from src.domain.repositories.user_repository import UserPage, UserRepository

__all__ = [
    "OptionalFieldRepository",
    "Pagination",
    "SongFilters",
    "SongPage",
    "SongRepository",
    "TaxonomyRepository",
    "UserPage",
    "UserRepository",
]
