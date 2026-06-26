from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import content_types
import libtorrent as libtorrent
from fastapi import Request

from app.common.constants import (
    CHUNK_SIZE,
    PRIO_2,
    PRIO_5,
    PRIO_7,
)
from app.common.logger import logger
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.relay.schemas import PieceOrFileAvailable


class Torrent:
    def __init__(
        self,
        torrent_handle: libtorrent.torrent_handle,
        torrent_info: TorrentInfo,
    ):
        self.torrent_handle = torrent_handle

        self.info_hash = torrent_info.info_hash
        self.name = torrent_info.name
        self.total_size = torrent_info.size

        self.piece_size = torrent_info.piece_size
        self.chunk_piece_count = math.ceil(CHUNK_SIZE / self.piece_size)

        piece_priorities = torrent_handle.piece_priorities()
        self._default_piece_priorities = piece_priorities
        self._active_piece_priorities = piece_priorities

        self.files: dict[int, File] = {}
        self._active_deadlines: list[int] = []

        for file_info in torrent_info.files:
            self.files[file_info.index] = File(
                file_info=file_info,
                torrent=self,
            )

    def priority_manager(self):
        try:
            priorities, piece_deadlines = self.get_priorities_and_deadlines()
            if priorities != self._active_piece_priorities:
                self.torrent_handle.prioritize_pieces(priorities)
                self._active_piece_priorities = priorities

            for piece_index in self._active_deadlines:
                if piece_index not in piece_deadlines:
                    self.torrent_handle.reset_piece_deadline(piece_index)

            for piece_index, deadline in piece_deadlines.items():
                self.torrent_handle.set_piece_deadline(piece_index, deadline)

            self._active_deadlines = list(piece_deadlines.keys())

        except Exception:
            logger.exception("Hiba történt a prioritáskezelőben.")

    def get_file(
        self,
        file_index: int,
    ) -> File | None:
        if file_index not in self.files:
            return None
        return self.files[file_index]

    def update_default_priorities(self, priority: int) -> None:
        self._default_piece_priorities = [priority] * len(
            self._default_piece_priorities
        )

    def get_priorities_and_deadlines(self) -> tuple[list[int], dict[int, int]]:
        priorities = self._default_piece_priorities.copy()
        piece_deadlines: dict[int, int] = {}

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

            for stream in list(file.streams.values()):
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
        file_info: TorrentFileInfo,
        torrent: Torrent,
    ):
        file_progress = torrent.torrent_handle.file_progress()

        self.torrent = torrent
        self.is_available = file_progress[file_info.index] == file_info.size
        self.file_index = file_info.index
        self.path = Path(torrent.torrent_handle.save_path()) / file_info.path
        self.name = file_info.name
        self.size = file_info.size
        self.offset = file_info.offset
        self.end_byte = self.size - 1
        self.start_piece_index = file_info.offset // torrent.piece_size
        self.end_piece_index = (file_info.offset + self.end_byte) // torrent.piece_size

        content_type = content_types.get_content_type(self.name)
        self.is_video = content_type.startswith("video/") if content_type else False

        self.streams: dict[str, Stream] = {}

    def calculate_meta_deadlines(self) -> dict[int, int] | None:
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

        deadlines: dict[int, int] = {}

        for piece_index in list(start_meta_indices) + list(end_meta_indices):
            if not self.torrent.torrent_handle.have_piece(piece_index):
                deadlines[piece_index] = 0

        if not deadlines:
            return None

        return deadlines

    async def stream(
        self,
        playback_id: str,
        user_id: str,
        stream_start_byte: int,
        stream_end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
        """A külső rétegek által hívott kényelmes belépési pont."""
        stream = Stream(
            stream_id=str(uuid4()),
            playback_id=playback_id,
            user_id=user_id,
            torrent=self.torrent,
            file=self,
            stream_start_byte=stream_start_byte,
            stream_end_byte=stream_end_byte,
        )

        return await stream.start(request)


class Stream:
    def __init__(
        self,
        stream_id: str,
        playback_id: str,
        user_id: str,
        torrent: Torrent,
        file: File,
        stream_start_byte: int,
        stream_end_byte: int,
    ):

        self.id = stream_id
        self.playback_id = playback_id
        self.user_id = user_id
        self.torrent = torrent
        self.file = file
        self.start_byte = stream_start_byte
        self.end_byte = stream_end_byte
        self.current_stream_byte = stream_start_byte

        stream_start_piece_index, stream_end_piece_index = self._get_byte_to_piece(
            stream_start_byte=stream_start_byte,
            stream_end_byte=stream_end_byte,
        )

        self.stream_start_piece_index = stream_start_piece_index
        self.stream_end_piece_index = stream_end_piece_index

        self.file.streams[self.id] = self

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

    def calculate_deadlines(self) -> tuple[dict[int, int], int]:
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

        deadlines: dict[int, int] = {}

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

    async def start(
        self,
        request: Request,
    ) -> AsyncIterator[bytes]:
        if self.file.is_available:
            return self._stream_with_cleanup(
                inner=self._file_iterator(
                    file_path=self.file.path,
                    start_byte=self.start_byte,
                    end_byte=self.end_byte,
                    request=request,
                ),
            )

        return self._stream_with_cleanup(
            inner=self._file_iterator_with_priorities(
                request=request,
            ),
        )

    async def _file_iterator_with_priorities(
        self,
        request: Request,
    ) -> AsyncIterator[bytes]:
        current_stream_byte = self.start_byte

        while current_stream_byte <= self.end_byte:
            if await request.is_disconnected():
                return

            self.set_pieces(
                stream_start_byte=current_stream_byte,
                stream_end_byte=self.end_byte,
            )

            current_end_byte = None
            while current_end_byte is None:
                if await request.is_disconnected():
                    return

                available_end_byte = await asyncio.to_thread(self._check_piece)

                if available_end_byte is not None:
                    current_end_byte = available_end_byte
                    break

                await asyncio.sleep(0.1)

            async for chunk in self._file_iterator(
                file_path=self.file.path,
                start_byte=current_stream_byte,
                end_byte=min(
                    current_end_byte,
                    self.end_byte,
                ),
                request=request,
            ):
                yield chunk

            current_stream_byte = current_end_byte + 1

    async def _stream_with_cleanup(
        self,
        inner: AsyncIterator[bytes],
    ) -> AsyncIterator[bytes]:
        try:
            async for chunk in inner:
                yield chunk
        finally:
            del self.file.streams[self.id]

    async def _file_iterator(
        self,
        file_path: Path,
        start_byte: int,
        end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
        self.current_stream_byte = start_byte

        with file_path.open("rb") as file_handle:
            await asyncio.to_thread(file_handle.seek, start_byte)

            remaining = end_byte - start_byte + 1

            while remaining > 0:
                if await request.is_disconnected():
                    return

                chunk = await asyncio.to_thread(
                    file_handle.read, min(CHUNK_SIZE, remaining)
                )

                if not chunk:
                    return

                remaining -= len(chunk)
                self.current_stream_byte += len(chunk)

                yield chunk

    def _check_piece(
        self,
    ) -> int | None:
        piece_or_file_available = self._check_piece_or_file_available()

        available_end_byte = None

        # A teljes file elérhetó, visszaadjuk az utolsó byte-ot.
        if piece_or_file_available.file_available:
            return self.file.end_byte

        if piece_or_file_available.piece_available:
            next_stream_piece_index = (
                self.stream_start_piece_index + self.torrent.chunk_piece_count
            )
            available_end_byte = (
                (next_stream_piece_index * self.torrent.piece_size)
                - self.file.offset
                - 1
            )

        return available_end_byte

    def _check_piece_or_file_available(
        self,
    ) -> PieceOrFileAvailable:
        piece_or_file_available = PieceOrFileAvailable(
            piece_available=False,
            file_available=False,
        )

        files_progress = self.torrent.torrent_handle.file_progress()
        file_progress = files_progress[self.file.file_index]

        file_available = file_progress == self.file.size

        if file_available:
            self.file.is_available = True
            piece_or_file_available.piece_available = True
            piece_or_file_available.file_available = True
            return piece_or_file_available

        stream_end_piece_index = min(
            self.stream_end_piece_index,
            self.stream_start_piece_index + self.torrent.chunk_piece_count,
        )
        prefech_pieces = range(
            self.stream_start_piece_index,
            stream_end_piece_index + 1,
        )

        pieces_available = True

        for prefech_piece in prefech_pieces:
            piece_available = self.torrent.torrent_handle.have_piece(
                prefech_piece,
            )

            if not piece_available:
                pieces_available = False
                break

        piece_or_file_available.piece_available = pieces_available

        return piece_or_file_available
