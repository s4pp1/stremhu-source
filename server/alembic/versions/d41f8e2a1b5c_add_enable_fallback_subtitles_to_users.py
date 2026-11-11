"""add_enable_fallback_subtitles_to_users

Revision ID: d41f8e2a1b5c
Revises: c30e6d9dd16d
Create Date: 2026-10-29 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d41f8e2a1b5c"
down_revision: str | None = "4b8c9d1e2f3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_fallback_subtitles",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("enable_fallback_subtitles")

