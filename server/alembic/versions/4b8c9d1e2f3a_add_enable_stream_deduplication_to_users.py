"""add_enable_stream_deduplication_to_users

Revision ID: 4b8c9d1e2f3a
Revises: 3a7b9c1d2e3f
Create Date: 2026-10-29 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b8c9d1e2f3a"
down_revision: str | None = "c30e6d9dd16d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_stream_deduplication",
                sa.Boolean(),
                server_default=sa.text("1"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("enable_stream_deduplication")

