"""Internal session epoch; existing signed cookies require a new login.

Revision ID: 6f0d92b1c843
Revises: 54a9d30f7c82
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6f0d92b1c843"
down_revision: str | None = "54a9d30f7c82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_epoch", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    # A binary rollback must also retire signed sessions: the old code ignores
    # epochs. Dropping this column alone cannot safely undo revocation.
    op.drop_column("users", "session_epoch")
