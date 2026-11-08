"""add nCore RSS catalog and manual mappings

Revision ID: d7e4b381b2c1
Revises: c30e6d9dd16d
Create Date: 2026-11-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e4b381b2c1"
down_revision: str | None = "c30e6d9dd16d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ncore_rss_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("feed_url", sa.String(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ncore_rss_settings")),
    )
    op.create_table(
        "ncore_rss_items",
        sa.Column("torrent_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("download_url", sa.String(), nullable=True),
        sa.Column("manual_download_url", sa.String(), nullable=True),
        sa.Column("detected_imdb_id", sa.String(), nullable=True),
        sa.Column("manual_imdb_id", sa.String(), nullable=True),
        sa.Column("last_detail_checked_at", sa.DateTime(), nullable=True),
        sa.Column("seeders", sa.Integer(), nullable=True),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("torrent_id", name=op.f("pk_ncore_rss_items")),
    )


def downgrade() -> None:
    op.drop_table("ncore_rss_items")
    op.drop_table("ncore_rss_settings")
