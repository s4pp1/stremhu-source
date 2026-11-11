"""add_enable_catalog_search_to_users

Revision ID: e72a1c3d4f5b
Revises: d41f8e2a1b5c
Create Date: 2026-10-30 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e72a1c3d4f5b"
down_revision: str | None = "d41f8e2a1b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_catalog_search",
                sa.Boolean(),
                server_default=sa.text("1"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("enable_catalog_search")

