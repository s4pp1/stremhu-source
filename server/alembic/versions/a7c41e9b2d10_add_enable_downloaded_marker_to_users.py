"""add_enable_downloaded_marker_to_users

Revision ID: a7c41e9b2d10
Revises: 6f0d92b1c843
Create Date: 2026-11-08 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c41e9b2d10"
down_revision: str | None = "6f0d92b1c843"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_downloaded_marker",
                sa.Boolean(),
                server_default=sa.text("1"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("enable_downloaded_marker")
