import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class NcoreRssSettingsModel(Base):
    __tablename__ = "ncore_rss_settings"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default="main")
    feed_url: Mapped[str] = mapped_column(sa.String)
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime, default=None
    )


class NcoreRssItemModel(Base):
    __tablename__ = "ncore_rss_items"

    torrent_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    title: Mapped[str] = mapped_column(sa.String)
    source_url: Mapped[str | None] = mapped_column(sa.String, default=None)
    download_url: Mapped[str | None] = mapped_column(sa.String, default=None)
    manual_download_url: Mapped[str | None] = mapped_column(sa.String, default=None)
    detected_imdb_id: Mapped[str | None] = mapped_column(sa.String, default=None)
    manual_imdb_id: Mapped[str | None] = mapped_column(sa.String, default=None)
    last_detail_checked_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime, default=None
    )
    seeders: Mapped[int | None] = mapped_column(sa.Integer, default=None)
    is_manual: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default_factory=datetime.datetime.now
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default_factory=datetime.datetime.now
    )
