import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.indexer_accounts.models import IndexerAccountModel

if TYPE_CHECKING:
    from app.modules.torrent_files.models import TorrentFileModel


class TorrentModel(Base):
    __tablename__ = "torrents"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["indexer_id", "torrent_id"],
            ["torrent_files.indexer_id", "torrent_files.torrent_id"],
            name="fk_torrents_torrent_files",
            ondelete="RESTRICT",
        ),
    )

    info_hash: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
    )

    indexer_id: Mapped[str] = mapped_column(
        sa.ForeignKey("indexer_accounts.indexer_id", ondelete="RESTRICT"),
        primary_key=True,
    )

    indexer_account: Mapped["IndexerAccountModel"] = relationship(
        "IndexerAccountModel",
        back_populates="torrents",
        uselist=False,
        init=False,
    )

    torrent_id: Mapped[str] = mapped_column(
        sa.String,
    )

    is_persisted: Mapped[bool] = mapped_column(sa.Boolean, default=False)

    full_download: Mapped[bool | None] = mapped_column(
        sa.Boolean,
        default=None,
    )

    resume_bytes: Mapped[bytes | None] = mapped_column(
        sa.LargeBinary,
        default=None,
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
    )

    torrent_file: Mapped["TorrentFileModel"] = relationship(
        "TorrentFileModel",
        back_populates="torrent",
        init=False,
        overlaps="indexer_account,torrents",
    )
