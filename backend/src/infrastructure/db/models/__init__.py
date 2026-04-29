"""ORM models — imported here so Alembic autogenerate sees the full metadata."""

from src.infrastructure.db.models.optional_field import (
    OptionalFieldDefinitionModel,
    SongOptionalFieldValueModel,
    optional_field_kind_enum,
)
from src.infrastructure.db.models.song import (
    ComposerModel,
    SongComposerLink,
    SongModel,
)
from src.infrastructure.db.models.taxonomy import (
    SongTaxonomyValueLink,
    TaxonomyValueModel,
    taxonomy_kind_enum,
)
from src.infrastructure.db.models.user_account import UserAccountModel, user_role_enum

__all__ = [
    "ComposerModel",
    "OptionalFieldDefinitionModel",
    "SongComposerLink",
    "SongModel",
    "SongOptionalFieldValueModel",
    "SongTaxonomyValueLink",
    "TaxonomyValueModel",
    "UserAccountModel",
    "optional_field_kind_enum",
    "taxonomy_kind_enum",
    "user_role_enum",
]
