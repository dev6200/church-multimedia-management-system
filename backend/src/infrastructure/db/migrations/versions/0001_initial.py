"""initial schema + pg_trgm + seed FR-020 / FR-021 values.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-28
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------- helpers
def _enum_create(name: str, *labels: str) -> str:
    quoted = ", ".join(f"'{label}'" for label in labels)
    return f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({quoted});
            END IF;
        END$$;
    """


def _enum_drop(name: str) -> str:
    return f"DROP TYPE IF EXISTS {name};"


# ---------------------------------------------------------------------- upgrade
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(_enum_create("user_role", "SUPER_ADMIN", "ADMIN", "USER"))
    op.execute(_enum_create("taxonomy_kind", "SEASON", "MASS", "SPECIAL_EVENT"))
    op.execute(_enum_create("optional_field_kind", "LINK"))

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_user_id", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.dialects.postgresql.CITEXT(), nullable=False, index=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "SUPER_ADMIN", "ADMIN", "USER", name="user_role", create_type=False
            ),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"])

    op.create_table(
        "composers",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "name_norm",
            sa.dialects.postgresql.CITEXT(),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_composers_name_trgm "
        "ON composers USING gin (name gin_trgm_ops)"
    )

    op.create_table(
        "taxonomy_values",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kind",
            sa.Enum(
                "SEASON",
                "MASS",
                "SPECIAL_EVENT",
                name="taxonomy_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_norm", sa.dialects.postgresql.CITEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint(
            "kind", "name_norm", name="uq_taxonomy_values_kind_name_norm"
        ),
    )

    op.create_table(
        "optional_field_definitions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column(
            "label_norm",
            sa.dialects.postgresql.CITEXT(),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "kind",
            sa.Enum("LINK", name="optional_field_kind", create_type=False),
            nullable=False,
            server_default="LINK",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "songs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("dedup_key", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_songs_updated_at_desc", "songs", ["updated_at"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_songs_title_trgm "
        "ON songs USING gin (title gin_trgm_ops)"
    )

    op.create_table(
        "song_composers",
        sa.Column(
            "song_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "composer_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("composers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("song_id", "composer_id"),
    )

    op.create_table(
        "song_taxonomy_values",
        sa.Column(
            "song_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "taxonomy_value_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("taxonomy_values.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("song_id", "taxonomy_value_id"),
    )

    op.create_table(
        "song_optional_field_values",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "song_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "definition_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("optional_field_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "song_id",
            "definition_id",
            name="uq_song_optional_field_values_song_definition",
        ),
    )

    # ----- Idempotent seeds (FR-020 / FR-021) ------------------------------
    # Use ON CONFLICT DO NOTHING so reruns are safe. Audit columns require a
    # creator user; for seeds we use a sentinel system UUID that any future
    # admin row can claim without breaking referential integrity.
    seed_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    op.execute(
        sa.text(
            """
            INSERT INTO user_accounts (id, clerk_user_id, email, display_name, role, version)
            VALUES (:id, :clerk_id, :email, :name, 'SUPER_ADMIN', 1)
            ON CONFLICT (clerk_user_id) DO NOTHING
            """
        ).bindparams(
            id=seed_user_id,
            clerk_id="system_seed",
            email="seed@system.local",
            name="System Seed",
        )
    )

    seed_seasons = [
        ("Advent", "advent"),
        ("Christmas", "christmas"),
        ("Lent", "lent"),
        ("Easter", "easter"),
        ("Ordinary Time", "ordinary time"),
    ]
    for name, norm in seed_seasons:
        op.execute(
            sa.text(
                """
                INSERT INTO taxonomy_values (
                    id, kind, name, name_norm,
                    created_by, updated_by, version
                )
                VALUES (
                    gen_random_uuid(), 'SEASON', :name, :norm,
                    :seed_user, :seed_user, 1
                )
                ON CONFLICT (kind, name_norm) DO NOTHING
                """
            ).bindparams(name=name, norm=norm, seed_user=seed_user_id)
        )

    seed_optional_fields = [
        ("PowerPoint link", "powerpoint link"),
        ("Sheet Music", "sheet music"),
        ("YouTube link", "youtube link"),
        ("Lyrics link", "lyrics link"),
    ]
    for label, norm in seed_optional_fields:
        op.execute(
            sa.text(
                """
                INSERT INTO optional_field_definitions (
                    id, label, label_norm, kind,
                    created_by, updated_by, version
                )
                VALUES (
                    gen_random_uuid(), :label, :norm, 'LINK',
                    :seed_user, :seed_user, 1
                )
                ON CONFLICT (label_norm) DO NOTHING
                """
            ).bindparams(label=label, norm=norm, seed_user=seed_user_id)
        )


# -------------------------------------------------------------------- downgrade
def downgrade() -> None:
    op.drop_table("song_optional_field_values")
    op.drop_table("song_taxonomy_values")
    op.drop_table("song_composers")
    op.drop_table("songs")
    op.drop_table("optional_field_definitions")
    op.drop_table("taxonomy_values")
    op.drop_table("composers")
    op.drop_table("user_accounts")

    op.execute(_enum_drop("optional_field_kind"))
    op.execute(_enum_drop("taxonomy_kind"))
    op.execute(_enum_drop("user_role"))
    # pg_trgm / citext extensions left in place — they are cluster-wide.
