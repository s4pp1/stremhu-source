"""add_uses_api_key_to_indexer_definitions

Revision ID: 7d4e2a9b1c5f
Revises: c30e6d9dd16d
Create Date: 2026-11-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d4e2a9b1c5f"
down_revision: str | None = "c30e6d9dd16d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("indexer_definitions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "uses_api_key",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("indexer_definitions", schema=None) as batch_op:
        batch_op.drop_column("uses_api_key")
