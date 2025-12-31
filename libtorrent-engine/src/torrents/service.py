import logging
import os
import threading
from typing import List

import libtorrent as libtorrent
from fastapi import HTTPException
from torrents.constants import (
    HIGH_PRIO_PREFETCH_PIECES,
    NORMAL_PRIO_PREFETCH_PIECES,
    PRIO_HIGH,
    PRIO_NORMAL,
)
from torrents.schemas import (
    AddTorrent,
    File,
    PiecesRangeAvailable,
    PrioritizeTorrentFile,
    Torrent,
)

logger = logging.getLogger(__name__)


class TorrentsService:
    def __init__(self) -> None:
        self.libtorrent_session = libtorrent.session()

        self.libtorrent_session.apply_settings(
            {
                "enable_upnp": True,
                "enable_natpmp": True,
                "enable_incoming_utp": True,
                "enable_incoming_tcp": True,
                "connections_limit": 200,
                "download_rate_limit": 12_500_000,
            }
        )

        # self.libtorrent_session.set_download_rate_limit(0)
        self.libtorrent_session.listen_on(666, 666)  # type: ignore[call-arg]

        self._lock = threading.RLock()
        self._last_prioritized: dict[str, tuple[int, int]] = {}

    def get_torrents(self) -> List[Torrent]:
        torrents = self.libtorrent_session.get_torrents()

        return [self._build_torrent(torrent) for torrent in torrents]

    def get_torrent_handle(
        self, info_hash: libtorrent.sha1_hash
    ) -> libtorrent.torrent_handle | None:
        torrent_handle = self.libtorrent_session.find_torrent(info_hash)

        if not torrent_handle.is_valid():
            return None

        return torrent_handle

    def get_torrent_handle_or_raise(
        self, info_hash: libtorrent.sha1_hash
    ) -> libtorrent.torrent_handle:
        torrent_handle = self.get_torrent_handle(info_hash=info_hash)

        if torrent_handle is None:
            raise HTTPException(404, f'"{info_hash}" torrent nem található.')

        return torrent_handle

    def get_torrent_or_raise(self, info_hash: libtorrent.sha1_hash) -> Torrent:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)
        return self._build_torrent(torrent_handle)

    def add_torrent(self, req: AddTorrent) -> Torrent:
        save_path = os.path.abspath(req.save_path)
        torrent_file_path = os.path.abspath(req.torrent_file_path)

        if not os.path.isfile(torrent_file_path):
            raise HTTPException(
                400, f'A(z) "{torrent_file_path}" torrent fájl nem található.'
            )

        torrent_info = libtorrent.torrent_info(torrent_file_path)
        info_hash = torrent_info.info_hash()

        existing_torrent_handle = self.get_torrent_handle(info_hash)
        if existing_torrent_handle is not None:
            self._build_torrent(existing_torrent_handle)

        with self._lock:
            torrent_info = libtorrent.torrent_info(torrent_file_path)

            os.makedirs(save_path, exist_ok=True)

            params = libtorrent.add_torrent_params()
            params.ti = torrent_info
            params.save_path = save_path

            torrent_handle = self.libtorrent_session.add_torrent(params)

            torrent_file = torrent_handle.torrent_file()
            if torrent_file is not None:
                files = torrent_file.files()

                files_priority = 0
                if req.download_full_torrent:
                    files_priority = 1

                torrent_handle.prioritize_files([files_priority] * files.num_files())

            torrent_status = torrent_handle.status()
            print(
                "state=",
                torrent_status.state,
                "paused=",
                torrent_status.paused,
                "peers=",
                torrent_status.num_peers,
                "candidates=",
                torrent_status.connect_candidates,
            )
            print("tracker=", torrent_handle.trackers()[0])

            return self._build_torrent(torrent_handle)

    def remove_torrent(self, info_hash: libtorrent.sha1_hash) -> Torrent:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)

        with self._lock:
            self.libtorrent_session.remove_torrent(
                torrent_handle,
                libtorrent.options_t.delete_files,
            )
            return self._build_torrent(torrent_handle)

    def get_torrent_file(
        self,
        info_hash: libtorrent.sha1_hash,
        file_index: int,
    ) -> File:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)

        file_progress = torrent_handle.file_progress()

        torrent_file = torrent_handle.torrent_file()

        if torrent_file is None:
            raise HTTPException(404, f'A(z) "{info_hash}" torrent nem található.')

        files = torrent_file.files()
        if file_index >= files.num_files():
            raise HTTPException(
                404, f'A(z) "{info_hash}, {file_index}" fájl nem található.'
            )

        file_entry = torrent_file.file_at(file_index)

        file_size = file_entry.size
        is_available = file_progress[file_index] == file_size

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

    def reset_pieces_priorities(
        self,
        info_hash: libtorrent.sha1_hash,
        file_index: int,
    ) -> None:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)
        priorities = torrent_handle.file_priorities()
        priorities[file_index] = 1
        torrent_handle.prioritize_files(priorities)

    def prioritize_pieces_range(
        self,
        info_hash: libtorrent.sha1_hash,
        file_index: int,
        req: PrioritizeTorrentFile,
    ) -> None:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)

        status = torrent_handle.status()
        if not status.has_metadata:
            raise HTTPException(
                409, "Torrent has no metadata yet (magnet still fetching)."
            )

        torrent_file = torrent_handle.torrent_file()
        if not torrent_file:
            raise HTTPException(
                409, "Torrent has no metadata yet (magnet still fetching)."
            )

        priorities = torrent_handle.piece_priorities()

        has_nonzero = any(priority > 0 for priority in priorities)
        if has_nonzero is False:
            torrent_handle.file_priority(file_index, 1)

        piece_size = int(torrent_file.piece_length())

        # boosted: List[int] = []

        files = torrent_file.files()
        if file_index < 0 or file_index >= files.num_files():
            raise HTTPException(400, "File index out of range")

        file_size = int(files.file_size(file_index))
        file_offset = int(files.file_offset(file_index))

        # file_piece_start = file_offset // piece_size
        file_piece_end = (file_offset + file_size - 1) // piece_size

        start_byte = max(0, req.start_byte)
        end_byte = min(req.end_byte, file_size - 1)

        if end_byte < start_byte:
            raise HTTPException(400, "endByte cannot be меньше than startByte")

        window_start_byte = start_byte
        window_end_byte = min(
            end_byte + (HIGH_PRIO_PREFETCH_PIECES * piece_size), file_size - 1
        )

        piece_start = self._piece_index_for_file_byte(
            piece_size, file_offset, window_start_byte
        )
        piece_end = (
            self._piece_index_for_file_byte(piece_size, file_offset, window_end_byte)
            + 1
        )

        # info_hash_key = str(info_hash)
        # last_range = self._last_prioritized.get(info_hash_key)
        # if last_range is not None:
        #     last_start, last_end = last_range
        #     for p in range(last_start, last_end):
        #         if p < piece_start or p >= piece_end:
        #             priorities[p] = PRIO_LOW

        for p in range(piece_start, piece_end):
            priorities[p] = int(PRIO_HIGH)
            # boosted.append(p)

        for prefetch_piece_index in range(NORMAL_PRIO_PREFETCH_PIECES):
            piece_index = piece_end + prefetch_piece_index
            if piece_index >= file_piece_end:
                break
            priorities[piece_index] = int(PRIO_NORMAL)

        torrent_handle.prioritize_pieces(priorities)
        # self._last_prioritized[info_hash_key] = (piece_start, piece_end)

    def check_pieces_range_available(
        self,
        info_hash: libtorrent.sha1_hash,
        file_index: int,
        start_byte: int,
        end_byte: int,
    ) -> PiecesRangeAvailable:
        torrent_handle = self.get_torrent_handle_or_raise(info_hash=info_hash)
        torrent_status = self._status_with_pieces(torrent_handle)

        pieces_range_available = PiecesRangeAvailable(
            ready=False,
            is_available=False,
        )

        torrent_file = torrent_handle.torrent_file()
        if torrent_file is None:
            return pieces_range_available

        files = torrent_file.files()
        if file_index < 0 or file_index >= files.num_files():
            raise HTTPException(
                404, f'A(z) "{info_hash}, {file_index}" fájl nem található.'
            )

        file_progress = torrent_handle.file_progress()
        file_size = int(files.file_size(file_index))

        is_available = file_progress[file_index] == file_size

        if is_available:
            pieces_range_available.ready = True
            pieces_range_available.is_available = is_available
            return pieces_range_available

        file_offset = int(files.file_offset(file_index))

        piece_size = int(torrent_file.piece_length())
        num_pieces = int(torrent_file.num_pieces())

        piece_start = self._piece_index_for_file_byte(
            piece_size, file_offset, start_byte
        )
        piece_end = (
            self._piece_index_for_file_byte(piece_size, file_offset, end_byte) + 1
        )

        piece_start = max(0, min(num_pieces, piece_start))
        piece_end = max(0, min(num_pieces, piece_end))

        if torrent_status.pieces is None:
            ready = True

            for i in range(piece_start, piece_end):
                if not torrent_handle.have_piece(i):
                    ready = False
                    break

            pieces_range_available.ready = ready
            return pieces_range_available

        ready = True
        for i in range(piece_start, piece_end):
            try:
                have = bool(torrent_status.pieces[i])
            except Exception:
                have = bool(torrent_handle.have_piece(i))
            if not have:
                ready = False
                break

        pieces_range_available.ready = ready
        return pieces_range_available

    def parse_info_hash(self, info_hash_str: str) -> libtorrent.sha1_hash:
        sha1_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return sha1_hash

    def _build_torrent(self, torrent_handle: libtorrent.torrent_handle) -> Torrent:
        status = torrent_handle.status()

        return Torrent(
            name=status.name,
            info_hash=str(status.info_hash),
            download_speed=status.download_rate,
            upload_speed=status.upload_rate,
            downloaded=status.total_done,
            uploaded=status.total_upload,
            progress=status.progress,
            total=status.total,
        )

    def _status_with_pieces(
        self, torrent_handle: libtorrent.torrent_handle
    ) -> libtorrent.torrent_status:
        # Some versions require query_pieces flag to populate st.pieces
        try:
            return torrent_handle.status(flags=libtorrent.status_flags_t.query_pieces)
        except Exception:
            return torrent_handle.status()

    def _piece_index_for_file_byte(
        self,
        piece_size: int,
        file_offset: int,
        file_byte: int,
    ) -> int:
        torrent_pos = file_offset + file_byte
        return int(torrent_pos // piece_size)
