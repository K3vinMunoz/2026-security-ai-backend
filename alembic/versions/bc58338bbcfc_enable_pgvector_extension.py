"""enable pgvector extension

Revision ID: bc58338bbcfc
Revises: 
Create Date: 2026-10-07 23:23:37.410396

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bc58338bbcfc'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable the PostgreSQL `vector` extension (pgvector).

    Infrastructure-only migration: no business tables exist yet. `IF NOT
    EXISTS` makes the migration idempotent if the extension was already enabled
    by other means.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Drop the `vector` extension.

    `IF EXISTS` guards against re-runs. No business objects depend on the
    extension yet, so plain DROP (without CASCADE) is safe and preferred: if a
    future table starts using vector columns, downgrading will require an
    explicit, reviewed decision to add CASCADE.
    """
    op.execute("DROP EXTENSION IF EXISTS vector")