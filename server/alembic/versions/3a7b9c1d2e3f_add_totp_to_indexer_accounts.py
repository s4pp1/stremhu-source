"""add_totp_to_indexer_accounts

Revision ID: 3a7b9c1d2e3f
Revises: 00e4b6a295c8
Create Date: 2026-08-10 12:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a7b9c1d2e3f"
down_revision: str | None = "00e4b6a295c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("indexer_accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("totp_secret", sa.String(), nullable=True))

    with op.batch_alter_table("indexer_definitions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "supports_totp",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("indexer_definitions", schema=None) as batch_op:
        batch_op.drop_column("supports_totp")

    with op.batch_alter_table("indexer_accounts", schema=None) as batch_op:
        batch_op.drop_column("totp_secret")
