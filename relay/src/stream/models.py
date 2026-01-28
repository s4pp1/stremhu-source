from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import libtorrent as libtorrent
from common.constants import (
    PREFETCH_HIGH_PIECES,
    PREFETCH_NORMAL_PIECES,
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

        self.torrent_handle = torrent_handle
        self.torrent_info = torrent_info

        self.piece_size = torrent_info.piece_length()
        self.default_priorities = priorities

        self.files: Dict[int, File] = {}

    def get_file(
        self,
        file_index: int,
    ) -> Optional[File]:
        if file_index not in self.files:
            return None
        return self.files[file_index]

    def get_or_raise_file(
        self,
        file_index: int,
    ) -> File:
        file = self.get_file(file_index)
        if not file:
            raise KeyError(f'A(z) "{file_index}" nem létezik.')
        return file

    def get_priorities(self) -> List[int]:
        priorities = self.default_priorities.copy()

        for priority_index, _ in enumerate(priorities):
            for file_index in self.files:
                file = self.files[file_index]
                file_range = range(file.start_piece_index, file.end_piece_index + 1)

                if priority_index in file_range:
                    priority = priorities[priority_index]

                    if priority < PRIO_2:
                        priority = PRIO_2

                    for stream_index in file.streams:
                        stream = file.streams[stream_index]

                        stream_range = range(
                            stream.stream_start_piece_index,
                            stream.stream_end_piece_index + 1,
                        )

                        if priority_index in stream_range:
                            stream_range_index = stream_range.index(priority_index)

                            if stream_range_index < PREFETCH_HIGH_PIECES:
                                priority = PRIO_7

                            elif (
                                stream_range_index < PREFETCH_NORMAL_PIECES
                                and priority < PRIO_5
                            ):
                                priority = PRIO_5

                    priorities[priority_index] = priority

        return priorities


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

    def get_priorities(self):
        priorities = self.torrent.get_priorities()

        stream_pieces_range = range(
            self.stream_start_piece_index, self.stream_end_piece_index
        )

        return priorities, self.stream_start_piece_index, len(stream_pieces_range)

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
