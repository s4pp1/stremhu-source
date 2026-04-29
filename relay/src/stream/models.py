from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import libtorrent as libtorrent
from common.constants import (
    CHUNK_SIZE,
    PRIO_2,
    PRIO_5,
    PRIO_7,
)
from fastapi import HTTPException


class Torrent:
    def __init__(
        self,
        torrent_handle: libtorrent.torrent_handle,
    ):
        torrent_info = torrent_handle.torrent_file()
        if torrent_info is None:
            raise HTTPException(
                404, f'"{torrent_handle.info_hash()}" torrent nem található.'
            )

        priorities = torrent_handle.piece_priorities().copy()

        self.info_hash = str(torrent_handle.info_hash())
        self.torrent_handle = torrent_handle
        self.torrent_info = torrent_info

        self.piece_size = torrent_info.piece_length()
        self.chunk_piece_count = math.ceil(CHUNK_SIZE / self.piece_size)
        self.default_priorities = priorities

        self.files: Dict[int, File] = {}
        self.active_deadlines: List[int] = []

    def add_file(self, file_index: int) -> File:
        file = File(
            file_index=file_index,
            torrent=self,
        )

        self.files[file_index] = file

        return file

    def drop_file(self, file_index: int) -> None:
        if file_index in self.files:
            del self.files[file_index]

    def get_file(
        self,
        file_index: int,
    ) -> Optional[File]:
        if file_index not in self.files:
            return None
        return self.files[file_index]

    def get_priorities_and_deadlines(self) -> Tuple[List[int], Dict[int, int]]:
        priorities = self.default_priorities.copy()
        piece_deadlines: Dict[int, int] = {}

        for file in self.files.values():
            if not file.streams:
                continue

            for piece_index in range(file.start_piece_index, file.end_piece_index + 1):
                priorities[piece_index] = PRIO_2

            meta_deadlines = file.calculate_meta_deadlines()

            priority = PRIO_7

            if meta_deadlines:
                for piece_index, piece_deadline in meta_deadlines.items():
                    priorities[piece_index] = priority
                    piece_deadlines[piece_index] = piece_deadline
                priority = PRIO_5

            for stream in file.streams.values():
                priority_pieces, priority_count = stream.calculate_deadlines()

                for index, (piece_index, piece_deadline) in enumerate(
                    priority_pieces.items()
                ):
                    priorities[piece_index] = max(priorities[piece_index], priority)

                    if index > priority_count:
                        continue

                    deadline = piece_deadline
                    if meta_deadlines:
                        deadline = deadline + 2500

                    if piece_index not in piece_deadlines:
                        piece_deadlines[piece_index] = deadline
                    else:
                        piece_deadlines[piece_index] = min(
                            piece_deadlines[piece_index], piece_deadline
                        )

        return priorities, piece_deadlines


class File:
    def __init__(
        self,
        file_index: int,
        torrent: Torrent,
    ):
        files_count = torrent.torrent_info.num_files()
        if file_index < 0 or file_index >= files_count:
            raise HTTPException(404, f'A(z) "{file_index}" fájl nem található.')

        file_progress = torrent.torrent_handle.file_progress()
        file_entry = torrent.torrent_info.file_at(file_index)
        file_size = file_entry.size
        file_path = Path(torrent.torrent_handle.save_path()) / file_entry.path

        self.torrent = torrent
        self.is_available = file_progress[file_index] == file_size
        self.file_index = file_index
        self.path = file_path
        self.name = file_path.name
        self.size = file_size
        self.offset = file_entry.offset
        self.end_byte = file_size - 1
        self.start_piece_index = file_entry.offset // torrent.piece_size
        self.end_piece_index = (file_entry.offset + file_size - 1) // torrent.piece_size

        self.streams: Dict[str, "Stream"] = {}

    def add_stream(
        self,
        stream_start_byte: int,
        stream_end_byte: int,
    ) -> "Stream":
        stream_id = uuid4().hex

        stream = Stream(
            stream_id=stream_id,
            torrent=self.torrent,
            file=self,
            stream_start_byte=stream_start_byte,
            stream_end_byte=stream_end_byte,
        )

        self.streams[stream_id] = stream

        return stream

    def drop_stream(self, stream_id: str) -> None:
        if stream_id in self.streams:
            del self.streams[stream_id]

    def get_stream(self, stream_id: str) -> Optional["Stream"]:
        if stream_id not in self.streams:
            return None
        return self.streams[stream_id]

    def calculate_meta_deadlines(self) -> Dict[int, int] | None:
        meta_piece_count = math.ceil(2 * 1024 * 1024 / self.torrent.piece_size)

        start_meta_indices = range(
            self.start_piece_index,
            min(
                self.end_piece_index + 1,
                self.start_piece_index + meta_piece_count,
            ),
        )

        end_meta_indices = range(
            max(
                self.start_piece_index,
                self.end_piece_index - meta_piece_count + 1,
            ),
            self.end_piece_index + 1,
        )

        deadlines: Dict[int, int] = {}

        for piece_index in list(start_meta_indices) + list(end_meta_indices):
            if not self.torrent.torrent_handle.have_piece(piece_index):
                deadlines[piece_index] = 0

        if not deadlines:
            return None

        return deadlines


class Stream:
    def __init__(
        self,
        stream_id: str,
        torrent: Torrent,
        file: File,
        stream_start_byte: int,
        stream_end_byte: int,
    ):
        self.id = stream_id
        self.torrent = torrent
        self.file = file
        self.start_byte = stream_start_byte
        self.end_byte = stream_end_byte

        stream_start_piece_index, stream_end_piece_index = self._get_byte_to_piece(
            stream_start_byte=stream_start_byte,
            stream_end_byte=stream_end_byte,
        )

        self.stream_start_piece_index = stream_start_piece_index
        self.stream_end_piece_index = stream_end_piece_index

    def drop(self) -> None:
        self.file.drop_stream(self.id)

    def set_pieces(
        self,
        stream_start_byte: int,
        stream_end_byte: int,
    ):
        stream_start_piece_index, stream_end_piece_index = self._get_byte_to_piece(
            stream_start_byte=stream_start_byte,
            stream_end_byte=stream_end_byte,
        )

        self.stream_start_piece_index = stream_start_piece_index
        self.stream_end_piece_index = stream_end_piece_index

        return stream_start_piece_index, stream_end_piece_index

    def _get_byte_to_piece(
        self,
        stream_start_byte: int,
        stream_end_byte: int,
    ):
        stream_start_piece_index = (
            stream_start_byte + self.file.offset
        ) // self.torrent.piece_size

        stream_end_piece_index = (
            stream_end_byte + self.file.offset
        ) // self.torrent.piece_size

        return stream_start_piece_index, stream_end_piece_index

    def calculate_deadlines(self) -> Tuple[Dict[int, int], int]:
        stream_count = len(self.file.streams)

        status = self.torrent.torrent_handle.status()
        download_speed = status.download_payload_rate

        stream_pieces_range = range(
            self.stream_start_piece_index, self.stream_end_piece_index + 1
        )

        one_mb_piece_count = math.ceil(1 * 1024 * 1024 / self.torrent.piece_size)

        critical_priority_count = one_mb_piece_count * 2

        high_priority_count = one_mb_piece_count * 10
        increment_ms = 250

        if download_speed > 0:
            high_priority_count = math.ceil(
                download_speed / self.torrent.piece_size / stream_count
            )
            ms_per_piece = (
                self.torrent.piece_size / (download_speed / stream_count)
            ) * 1000
            increment_ms = int(max(100, min(2000, ms_per_piece)))

        priority_count = high_priority_count * 3

        deadlines: Dict[int, int] = {}

        active_piece_count = 0
        downloaded_piece_count = 0

        for piece_index in stream_pieces_range:
            if active_piece_count >= priority_count:
                break

            if self.torrent.torrent_handle.have_piece(piece_index):
                downloaded_piece_count += 1
                continue

            current_index = active_piece_count + downloaded_piece_count

            deadline_count = max(0, current_index - critical_priority_count)
            if piece_index not in deadlines:
                deadlines[piece_index] = increment_ms * deadline_count
            active_piece_count += 1

        return deadlines, high_priority_count
