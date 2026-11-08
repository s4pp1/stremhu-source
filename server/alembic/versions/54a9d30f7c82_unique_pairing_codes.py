"""Unique ephemeral pairing codes; existing devices must start pairing again.

Revision ID: 54a9d30f7c82
Revises: e72a1c3d4f5b
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "54a9d30f7c82"
down_revision: str | None = "e72a1c3d4f5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Pairings are disposable; users and their credentials must remain intact.
    op.execute(sa.text("DELETE FROM pairings"))
    for column in ("user_code", "device_code"):
        name = f"ix_pairings_{column}"
        op.drop_index(name, table_name="pairings")
        op.create_index(name, "pairings", [column], unique=True)


def downgrade() -> None:
    for column in ("user_code", "device_code"):
        name = f"ix_pairings_{column}"
        op.drop_index(name, table_name="pairings")
        op.create_index(name, "pairings", [column], unique=False)
