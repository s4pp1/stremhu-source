import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, Dict

import content_types
import libtorrent as libtorrent
from common.constants import (
    CHUNK_SIZE,
)
from fastapi import HTTPException, Request
from libtorrent_client.service import LibtorrentClientService
from stream.models import File, Stream, Torrent
from stream.schemas import (
    ParsedRangeHeader,
    PieceOrFileAvailable,
)

logger = logging.getLogger(__name__)


class StreamService:
    def __init__(
        self,
        libtorrent_client_service: LibtorrentClientService,
    ):
        self.libtorrent_client_service = libtorrent_client_service
        self.torrents: Dict[str, Torrent] = {}

    async def priority_manager_loop(self):
        while True:
            try:
                for torrent in self.torrents.values():
                    priorities, piece_deadlines = torrent.get_priorities_and_deadlines()

                    torrent.torrent_handle.prioritize_pieces(priorities)

                    for piece_index in torrent.active_deadlines:
                        if piece_index not in piece_deadlines:
                            torrent.torrent_handle.reset_piece_deadline(piece_index)

                    for piece_index, deadline in piece_deadlines.items():
                        torrent.torrent_handle.set_piece_deadline(piece_index, deadline)

                    torrent.active_deadlines = list(piece_deadlines.keys())

            except Exception as e:
                logger.error(f"Hiba történt a prioritáskezelőben: {e}")

            await asyncio.sleep(0.1)

    def validate_torrent_file(
        self,
        info_hash: str,
        file_index: int,
    ) -> File:
        torrent = self.torrents.get(info_hash)
        if not torrent:
            raise HTTPException(404, f'A(z) "{info_hash}" torrent nem található.')

        file = torrent.get_file(file_index)
        if not file:
            raise HTTPException(
                404, f"A(z) '{info_hash}' torrent {file_index} fájlja nem található."
            )

        return file

    def register_torrent(self, torrent_handle: libtorrent.torrent_handle) -> Torrent:
        info_hash_str = str(torrent_handle.info_hash())

        if info_hash_str in self.torrents:
            return self.torrents[info_hash_str]

        torrent = Torrent(torrent_handle=torrent_handle)
        self.torrents[info_hash_str] = torrent

        torrent_info = torrent_handle.torrent_file()
        if torrent_info:
            for file_index in range(torrent_info.num_files()):
                file_entry = torrent_info.file_at(file_index)
                content_type = content_types.get_content_type(file_entry.path)

                if content_type and content_type.startswith("video/"):
                    torrent.add_file(
                        file_index=file_index,
                    )

        return torrent

    def remove_torrent(self, info_hash: str):
        if info_hash in self.torrents:
            self.torrents.pop(info_hash)

    def prepare_for_stream(
        self,
        file: File,
        range_header: str | None = None,
    ) -> Stream:
        parsed_range_header = self._parse_range_header(
            file_size=file.size,
            range_header=range_header,
        )

        stream = file.add_stream(
            stream_start_byte=parsed_range_header.start_byte,
            stream_end_byte=parsed_range_header.end_byte,
        )

        return stream

    async def stream(
        self,
        stream: Stream,
        request: Request,
    ) -> AsyncIterator[bytes]:
        if stream.file.is_available:
            return self._stream_with_cleanup(
                stream=stream,
                inner=self._file_iterator(
                    file_path=stream.file.path,
                    start_byte=stream.start_byte,
                    end_byte=stream.end_byte,
                    request=request,
                ),
            )

        return self._stream_with_cleanup(
            stream=stream,
            inner=self._file_iterator_with_priorities(
                stream=stream,
                request=request,
            ),
        )

    def _parse_range_header(
        self,
        file_size: int,
        range_header: str | None = None,
    ) -> ParsedRangeHeader:
        if range_header is None:
            return ParsedRangeHeader(
                start_byte=0,
                end_byte=file_size - 1,
                content_length=file_size,
            )

        if not range_header.startswith("bytes="):
            raise HTTPException(416, "Érvénytelen range header.")

        range_value = range_header.replace("bytes=", "", 1).strip()
        if "," in range_value:
            raise HTTPException(416, "A több tartomány nem támogatott.")

        start_byte_str, end_byte_str = range_value.split("-", 1)

        if start_byte_str == "":
            if not end_byte_str:
                raise HTTPException(416, "Érvénytelen range header.")

            suffix_length = int(end_byte_str)
            if suffix_length <= 0:
                raise HTTPException(416, "Érvénytelen range header.")

            start_byte = max(file_size - suffix_length, 0)
            end_byte = file_size - 1
        else:
            start_byte = int(start_byte_str)
            end_byte = int(end_byte_str) if end_byte_str else file_size - 1

        if (
            start_byte < 0
            or end_byte < 0
            or start_byte > end_byte
            or end_byte >= file_size
        ):
            raise HTTPException(416, "A kért tartomány kívül esik a fájlon.")

        content_length = end_byte - start_byte + 1

        return ParsedRangeHeader(
            start_byte=start_byte,
            end_byte=end_byte,
            content_length=content_length,
        )

    async def _file_iterator_with_priorities(
        self,
        stream: Stream,
        request: Request,
    ) -> AsyncIterator[bytes]:
        current_stream_byte = stream.start_byte

        while current_stream_byte <= stream.end_byte:
            if await request.is_disconnected():
                return

            stream.set_pieces(
                stream_start_byte=current_stream_byte,
                stream_end_byte=stream.end_byte,
            )

            current_end_byte = None
            while current_end_byte is None:
                if await request.is_disconnected():
                    return

                available_end_byte = self._check_piece(
                    stream=stream,
                )

                if available_end_byte is not None:
                    current_end_byte = available_end_byte
                    break

                await asyncio.sleep(0.1)

            async for chunk in self._file_iterator(
                file_path=stream.file.path,
                start_byte=current_stream_byte,
                end_byte=min(
                    current_end_byte,
                    stream.end_byte,
                ),
                request=request,
            ):
                yield chunk

            current_stream_byte = current_end_byte + 1

    async def _stream_with_cleanup(
        self,
        stream: Stream,
        inner: AsyncIterator[bytes],
    ) -> AsyncIterator[bytes]:
        try:
            async for chunk in inner:
                yield chunk
        finally:
            stream.drop()

    async def _file_iterator(
        self,
        file_path: Path,
        start_byte: int,
        end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
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

                yield chunk

    def _check_piece(
        self,
        stream: Stream,
    ) -> int | None:
        piece_or_file_available = self._check_piece_or_file_available(
            stream=stream,
        )

        available_end_byte = None

        # A teljes file elérhetó, visszaadjuk az utolsó byte-ot.
        if piece_or_file_available.file_available:
            return stream.file.end_byte

        if piece_or_file_available.piece_available:
            next_stream_piece_index = (
                stream.stream_start_piece_index + stream.torrent.chunk_piece_count
            )
            available_end_byte = (
                (next_stream_piece_index * stream.torrent.piece_size)
                - stream.file.offset
                - 1
            )

        return available_end_byte

    def _check_piece_or_file_available(
        self,
        stream: Stream,
    ) -> PieceOrFileAvailable:
        piece_or_file_available = PieceOrFileAvailable(
            piece_available=False,
            file_available=False,
        )

        files_progress = stream.torrent.torrent_handle.file_progress()
        file_progress = files_progress[stream.file.file_index]

        file_available = file_progress == stream.file.size

        if file_available:
            stream.file.is_available = True
            piece_or_file_available.piece_available = True
            piece_or_file_available.file_available = True
            return piece_or_file_available

        stream_end_piece_index = min(
            stream.stream_end_piece_index,
            stream.stream_start_piece_index + stream.torrent.chunk_piece_count,
        )
        prefech_pieces = range(
            stream.stream_start_piece_index,
            stream_end_piece_index + 1,
        )

        pieces_available = True

        for prefech_piece in prefech_pieces:
            piece_available = stream.torrent.torrent_handle.have_piece(
                prefech_piece,
            )

            if not piece_available:
                pieces_available = False
                break

        piece_or_file_available.piece_available = pieces_available

        return piece_or_file_available
