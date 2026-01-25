import logging
from typing import List

import libtorrent as libtorrent
from common.constants import PRIO_LOW, PRIO_SKIP
from libtorrent_client.service import LibtorrentClientService
from torrents.schemas import (
    AddTorrent,
    RelayTorrent,
    RelayTorrentState,
)

logger = logging.getLogger(__name__)


class TorrentsService:
    def __init__(
        self,
        libtorrent_client_service: LibtorrentClientService,
    ) -> None:
        self.libtorrent_client_service = libtorrent_client_service

    def add_torrent(
        self,
        payload: AddTorrent,
    ) -> RelayTorrent:
        priority = PRIO_SKIP
        if payload.download_full_torrent:
            priority = PRIO_LOW

        torrent_handle = self.libtorrent_client_service.add_torrent(
            save_path=payload.save_path,
            torrent_file_path=payload.torrent_file_path,
            priority=priority,
        )

        return self._build_torrent(torrent_handle)

    def get_torrents(self) -> List[RelayTorrent]:
        torrent_handlers = self.libtorrent_client_service.get_torrents()

        return [
            self._build_torrent(torrent_handle) for torrent_handle in torrent_handlers
        ]

    def get_torrent_or_raise(
        self,
        info_hash: str,
    ) -> RelayTorrent:
        info_hash_sha1 = self.libtorrent_client_service.parse_info_hash(info_hash)
        torrent_handle = self.libtorrent_client_service.get_torrent_or_raise(
            info_hash=info_hash_sha1
        )

        return self._build_torrent(torrent_handle)

    def get_torrent_state(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> RelayTorrentState:
        torrent_handle = self.libtorrent_client_service.get_torrent_or_raise(
            info_hash=info_hash
        )

        return self._torrent_state(
            torrent_handle=torrent_handle,
        )

    def remove_torrent(
        self,
        info_hash: str,
    ):
        torrent = self.get_torrent_or_raise(
            info_hash=info_hash,
        )

        info_hash_sha1 = self.libtorrent_client_service.parse_info_hash(info_hash)

        self.libtorrent_client_service.remove_torrent(
            info_hash=info_hash_sha1,
        )

        return torrent

    def parse_info_hash(self, info_hash_str: str) -> libtorrent.sha1_hash:
        sha1_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return sha1_hash

    def _torrent_state(
        self,
        torrent_handle: libtorrent.torrent_handle,
    ) -> RelayTorrentState:
        torrent_status = torrent_handle.status()
        return RelayTorrentState(
            state=torrent_status.state,
            progress=torrent_status.progress,
        )

    def _build_torrent(
        self,
        torrent_handle: libtorrent.torrent_handle,
    ) -> RelayTorrent:
        status = torrent_handle.status()

        total = 0
        torrent_info = torrent_handle.torrent_file()
        if torrent_info:
            total = torrent_info.total_size()

        return RelayTorrent(
            name=status.name,
            info_hash=str(status.info_hash),
            download_speed=status.download_payload_rate,
            upload_speed=status.upload_payload_rate,
            downloaded=status.total_done,
            uploaded=status.total_payload_upload,
            state=status.state,
            progress=status.progress,
            total=total,
        )
