import asyncio
from typing import AsyncIterator, Dict
from uuid import uuid4

import libtorrent as libtorrent
from fastapi import HTTPException, Request
from libtorrent_client.service import LibtorrentClientService
from stream.models import File, Stream, Torrent
from stream.schemas import (
    ParsedRangeHeader,
    PieceOrFileAvailable,
    PlaybackResponse,
)


class StreamService:
    def __init__(
        self,
        libtorrent_client_service: LibtorrentClientService,
    ):
        self.libtorrent_client_service = libtorrent_client_service
        self.torrents: Dict[str, Torrent] = {}

    async def stream(
        self,
        info_hash: str,
        file_index: int,
        request: Request,
        range_header: str | None = None,
    ) -> PlaybackResponse:
        torrent_handle = self.libtorrent_client_service.get_torrent_or_raise(
            libtorrent.sha1_hash(bytes.fromhex(info_hash))
        )

        # Torrent megkeresése vagy létrehozása
        torrent = Torrent(
            torrent_handle=torrent_handle,
        )

        if info_hash in self.torrents:
            torrent = self.torrents[info_hash]

        # File megkeresése vagy létrehozása
        torrent_file = File(
            file_index=file_index,
            torrent=torrent,
        )

        if file_index in torrent.files:
            torrent_file = torrent.files[file_index]

        # Range header elemzése
        parsed_range_header = self._parse_range_header(
            file_size=torrent_file.size,
            range_header=range_header,
        )

        if torrent_file.is_available:
            return PlaybackResponse(
                iterator=self._file_iterator(
                    torrent_file=torrent_file,
                    stream_start_byte=parsed_range_header.start_byte,
                    stream_end_byte=parsed_range_header.end_byte,
                    request=request,
                ),
                file_size=torrent_file.size,
                start_byte=parsed_range_header.start_byte,
                end_byte=parsed_range_header.end_byte,
                file_name=torrent_file.name,
            )

        if info_hash in self.torrents:
            torrent = self.torrents[info_hash]

            if file_index in torrent.files:
                torrent_file = torrent.files[file_index]
            else:
                torrent.files[file_index] = torrent_file
        else:
            self.torrents[info_hash] = torrent
            torrent.files[file_index] = torrent_file

        return PlaybackResponse(
            iterator=self._file_iterator_with_priorities(
                torrent_file=torrent_file,
                stream_start_byte=parsed_range_header.start_byte,
                stream_end_byte=parsed_range_header.end_byte,
                request=request,
            ),
            file_size=torrent_file.size,
            start_byte=parsed_range_header.start_byte,
            end_byte=parsed_range_header.end_byte,
            file_name=torrent_file.name,
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

        return ParsedRangeHeader(
            start_byte=start_byte,
            end_byte=end_byte,
            content_length=file_size,
        )

    async def _file_iterator_with_priorities(
        self,
        torrent_file: File,
        stream_start_byte: int,
        stream_end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
        stream_id = uuid4().hex

        current_stream_byte = stream_start_byte

        stream = Stream(
            stream_id=stream_id,
            torrent=torrent_file.torrent,
            file=torrent_file,
            stream_start_byte=current_stream_byte,
            stream_end_byte=stream_end_byte,
        )

        torrent_file.streams[stream_id] = stream

        try:
            while current_stream_byte <= stream_end_byte:
                if await request.is_disconnected():
                    return

                stream.set_pieces(
                    stream_start_byte=current_stream_byte,
                    stream_end_byte=stream_end_byte,
                )

                current_end_byte = None

                while current_end_byte is None:
                    if await request.is_disconnected():
                        return

                    available_end_byte = self._check_piece_and_prioritize(
                        stream=stream,
                    )

                    if available_end_byte is not None:
                        current_end_byte = available_end_byte
                        break

                    await asyncio.sleep(0.2)

                async for chunk in self._file_iterator(
                    torrent_file=torrent_file,
                    stream_start_byte=current_stream_byte,
                    stream_end_byte=current_end_byte,
                    request=request,
                ):
                    yield chunk

                current_stream_byte = current_end_byte + 1
        finally:
            self._end_stream(
                stream=stream,
            )

    async def _file_iterator(
        self,
        torrent_file: File,
        stream_start_byte: int,
        stream_end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
        with torrent_file.path.open("rb") as file_handle:
            file_handle.seek(stream_start_byte)

            remaining = stream_end_byte - stream_start_byte + 1

            while remaining > 0:
                if await request.is_disconnected():
                    return

                chunk = file_handle.read(
                    min(torrent_file.torrent.piece_size, remaining)
                )

                if not chunk:
                    return

                remaining -= len(chunk)

                yield chunk

    def _check_piece_and_prioritize(
        self,
        stream: Stream,
    ) -> int | None:
        piece_or_file_available = self._check_piece_or_file_available(
            stream=stream,
        )

        available_end_byte = None

        # Már le van töltve, csak visszaadjuk a végét és mehet a lejátszás.
        if piece_or_file_available.file_available:
            return stream.file.end_byte

        if piece_or_file_available.piece_available:
            next_stream_piece_index = stream.stream_start_piece_index + 1
            available_end_byte = (
                (next_stream_piece_index * stream.torrent.piece_size)
                - stream.file.offset
                - 1
            )

        # Prefetch beállítása
        priorities, critical_piece_index, prefetch_piece_count = stream.get_priorities()

        stream.torrent.torrent_handle.prioritize_pieces(priorities)

        # Kritikus piece kérése
        set_piece_count = 1
        for count_index in range(prefetch_piece_count):
            if set_piece_count > 4:
                break

            piece_index = critical_piece_index + count_index
            if stream.torrent.torrent_handle.have_piece(piece_index):
                continue

            stream.torrent.torrent_handle.set_piece_deadline(
                piece_index, 200 * set_piece_count
            )
            set_piece_count += 1

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
            piece_or_file_available.piece_available = True
            piece_or_file_available.file_available = True
            return piece_or_file_available

        piece_available = stream.torrent.torrent_handle.have_piece(
            stream.stream_start_piece_index
        )

        piece_or_file_available.piece_available = piece_available

        return piece_or_file_available

    def _end_stream(
        self,
        stream: Stream,
    ):
        torrent = stream.torrent
        file = stream.file

        file.streams.pop(stream.id)

        if not file.streams:
            torrent.files.pop(file.file_index)

        if not torrent.files:
            torrent.torrent_handle.prioritize_pieces(torrent.default_priorities)

            info_hash = torrent.torrent_info.info_hash()
            self.torrents.pop(str(info_hash))
