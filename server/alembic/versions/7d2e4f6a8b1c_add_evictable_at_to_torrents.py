"""Add evictable_at to TorrentModel

Revision ID: 7d2e4f6a8b1c
Revises: c30e6d9dd16d
Create Date: 2026-11-11 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d2e4f6a8b1c"
down_revision: str | None = "c30e6d9dd16d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("torrents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("evictable_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("torrents", schema=None) as batch_op:
        batch_op.drop_column("evictable_at")
