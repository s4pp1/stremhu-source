import logging
from typing import List

import libtorrent as libtorrent
from common.constants import PRIO_LOW, PRIO_SKIP
from fastapi import HTTPException
from libtorrent_client.service import LibtorrentClientService
from torrents.schemas import (
    AddTorrent,
    File,
    FileDetails,
    PieceOrFileAvailable,
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

    def get_torrent_file(
        self,
        info_hash: libtorrent.sha1_hash,
        file_index: int,
    ) -> File:
        torrent_handle = self.libtorrent_client_service.get_torrent_or_raise(
            info_hash=info_hash
        )

        torrent_file = torrent_handle.torrent_file()

        if torrent_file is None:
            raise HTTPException(404, f'A(z) "{info_hash}" torrent nem található.')

        files = torrent_file.files()
        if file_index >= files.num_files():
            raise HTTPException(
                404, f'A(z) "{info_hash}, {file_index}" fájl nem található.'
            )

        file_size = files.file_size(file_index)
        file_entry = torrent_file.file_at(file_index)

        is_available = self._check_file_available(
            torrent_handle=torrent_handle,
            file_index=file_index,
        )

        file = File(
            info_hash=str(torrent_handle.info_hash()),
            file_index=file_index,
            piece_length=torrent_file.piece_length(),
            path=file_entry.path,
            offset=file_entry.offset,
            size=file_size,
            is_available=is_available,
        )

        return file

    def parse_info_hash(self, info_hash_str: str) -> libtorrent.sha1_hash:
        sha1_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return sha1_hash

    def _get_file_details(
        self,
        torrent_file: libtorrent.torrent_info,
        file_index: int,
    ) -> FileDetails:
        files = torrent_file.files()

        if file_index < 0 or file_index >= files.num_files():
            raise HTTPException(400, f'A(z) "{file_index}" fálj nem létezik.')

        piece_size = int(torrent_file.piece_length())

        file_offset = int(files.file_offset(file_index))
        file_size = int(files.file_size(file_index))

        file_start_piece_index = file_offset // piece_size
        file_end_piece_index = (file_offset + file_size - 1) // piece_size

        return FileDetails(
            file_start_piece_index=file_start_piece_index,
            file_end_byte=file_size - 1,
            file_end_piece_index=file_end_piece_index,
            piece_size=piece_size,
            file_offset=file_offset,
            file_size=file_size,
        )

    def _check_file_available(
        self,
        torrent_handle: libtorrent.torrent_handle,
        file_index: int,
    ) -> bool:
        torrent_file = torrent_handle.torrent_file()
        if torrent_file is None:
            return False

        file_progress = torrent_handle.file_progress()
        file_entry = torrent_file.file_at(file_index)

        file_size = file_entry.size
        is_available = file_progress[file_index] == file_size
        return is_available

    def _check_piece_or_file_available(
        self,
        torrent_handle: libtorrent.torrent_handle,
        file_index: int,
        piece_index: int,
    ) -> PieceOrFileAvailable:
        piece_or_file_available = PieceOrFileAvailable(
            piece_available=False,
            file_available=False,
        )

        torrent_file = torrent_handle.torrent_file()
        if torrent_file is None:
            return piece_or_file_available

        files_progress = torrent_handle.file_progress()
        file_progress = files_progress[file_index]
        file_entry = torrent_file.file_at(file_index)

        file_available = file_progress == file_entry.size

        if file_available:
            piece_or_file_available.piece_available = True
            piece_or_file_available.file_available = True
            return piece_or_file_available

        piece_available = torrent_handle.have_piece(piece_index)
        piece_or_file_available.piece_available = piece_available

        return piece_or_file_available

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
