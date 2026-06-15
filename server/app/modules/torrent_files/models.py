import datetime
from dataclasses import field

import libtorrent as libtorrent
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common.database import Base
from app.common.torrent_info import TorrentInfo, parse_torrent_info
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.torrent_files.exceptions import InvalidTorrentFileException
from app.modules.torrents.models import TorrentModel


class TorrentFileModel(Base):
    __tablename__ = "torrent_files"

    indexer_id: Mapped[str] = mapped_column(
        sa.ForeignKey("indexer_accounts.indexer_id", ondelete="CASCADE"),
        primary_key=True,
    )

    indexer_account: Mapped["IndexerAccountModel"] = relationship(
        "IndexerAccountModel",
        uselist=False,
        init=False,
    )

    torrent_id: Mapped[str] = mapped_column(sa.String, primary_key=True)

    info_hash: Mapped[str] = mapped_column(
        sa.String,
        index=True,
        init=False,
    )

    torrent_bytes: Mapped[bytes] = mapped_column(sa.LargeBinary)

    last_used_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
    )

    torrent: Mapped[TorrentModel | None] = relationship(
        "TorrentModel",
        back_populates="torrent_file",
        uselist=False,
        init=False,
        overlaps="indexer_account,torrents",
    )

    _cached_info: TorrentInfo | None = field(default=None, init=False, repr=False)

    @validates("torrent_bytes")
    def validate_torrent_bytes(self, _: str, value: bytes) -> bytes:
        self._cached_info = self._torrent_info(value)
        self.info_hash = self._cached_info.info_hash
        return value

    @property
    def info(self) -> TorrentInfo:
        if self._cached_info is None:
            self._cached_info = self._torrent_info(self.torrent_bytes)
        return self._cached_info

    def _torrent_info(self, torrent: bytes | libtorrent.torrent_info) -> TorrentInfo:
        try:
            return parse_torrent_info(torrent)
        except Exception:
            raise InvalidTorrentFileException()
