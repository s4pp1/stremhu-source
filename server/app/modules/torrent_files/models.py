import datetime
import threading
from dataclasses import field

import libtorrent as libtorrent
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common.database import Base
from app.common.torrent_info import TorrentInfo, parse_torrent_info
from app.config import config
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.torrent_files.exceptions import InvalidTorrentFileException
from app.modules.torrents.models import TorrentModel

_TORRENT_INFO_CACHE: dict[str, TorrentInfo] = {}
_MAX_TORRENT_INFO_CACHE = 2000
_cache_lock = threading.Lock()
_cached_files = 0


def _weight(info: TorrentInfo) -> int:
    return len(info.files) + 1


def _cache_torrent_info(info: TorrentInfo) -> None:
    """Darabszámra (2000) és fájlbejegyzésre (``torrent_info_cache_max_files``) korlátos, beszúrási sorrendben ürülő cache.

    CR15/c (27): egy 10 000 fájlos info ~13 MiB; darabszám-korláttal a cache GiB-os méretűre nőhetett.
    Szálakból is hívódik (mentés, snapshot-olvasás), ezért zár védi.
    """
    global _cached_files
    weight = _weight(info)
    limit = config.torrent_info_cache_max_files
    with _cache_lock:
        if not _TORRENT_INFO_CACHE:
            _cached_files = 0  # külső clear() után
        old = _TORRENT_INFO_CACHE.pop(info.info_hash, None)
        if old is not None:
            _cached_files -= _weight(old)
        if weight > limit:
            return
        while _TORRENT_INFO_CACHE and (len(_TORRENT_INFO_CACHE) >= _MAX_TORRENT_INFO_CACHE or _cached_files + weight > limit):
            oldest = next(iter(_TORRENT_INFO_CACHE))
            _cached_files -= _weight(_TORRENT_INFO_CACHE.pop(oldest))
        _TORRENT_INFO_CACHE[info.info_hash] = info
        _cached_files += weight


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
        _cache_torrent_info(self._cached_info)
        return value

    @property
    def info(self) -> TorrentInfo:
        if getattr(self, "_cached_info", None) is not None:
            return self._cached_info  # type: ignore[return-value]
        info_hash = getattr(self, "info_hash", None)
        if info_hash and info_hash in _TORRENT_INFO_CACHE:
            self._cached_info = _TORRENT_INFO_CACHE[info_hash]
            return self._cached_info
        self._cached_info = self._torrent_info(self.torrent_bytes)
        return self._cached_info

    def _torrent_info(self, torrent: bytes | libtorrent.torrent_info) -> TorrentInfo:
        try:
            parsed = parse_torrent_info(torrent)
            _cache_torrent_info(parsed)
            return parsed
        except Exception:
            raise InvalidTorrentFileException()
