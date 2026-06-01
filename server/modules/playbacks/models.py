from datetime import datetime

import sqlalchemy as sa
from common.database import Base
from sqlalchemy.orm import Mapped, mapped_column


class Playback(Base):
    __tablename__ = "playbacks"
    __table_args__ = (
        sa.Index(
            "ix_playback_user_torrent_file_index", "user_id", "torrent_id", "file_index"
        ),
        sa.Index("ix_playback_last_seen", "last_seen_at"),
    )

    session_id: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(sa.String)

    indexer_id: Mapped[str] = mapped_column(sa.String)

    torrent_id: Mapped[str] = mapped_column(sa.String)

    file_index: Mapped[int] = mapped_column(sa.Integer)

    client_type: Mapped[str | None] = mapped_column(sa.String)

    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.now,
    )
