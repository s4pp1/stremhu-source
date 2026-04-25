import asyncio
import json
import logging
import math
from pathlib import Path
from typing import AsyncIterator, Dict, Optional
from uuid import uuid4

import content_types
import libtorrent as libtorrent
import pydash
from common.constants import (
    METADATA_FETCH_SIZE,
    PRIO_7,
)
from fastapi import HTTPException, Request
from ffmpeg.asyncio import FFmpeg  # type: ignore
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
        self._metadata_tasks: Dict[str, asyncio.Task[None]] = {}

    def register_torrent(self, torrent_handle: libtorrent.torrent_handle) -> Torrent:
        info_hash_str = str(torrent_handle.info_hash())

        if info_hash_str in self.torrents:
            return self.torrents[info_hash_str]

        torrent = Torrent(torrent_handle=torrent_handle)
        self.torrents[info_hash_str] = torrent

        torrent_info = torrent_handle.torrent_file()
        if torrent_info:
            for i in range(torrent_info.num_files()):
                file_entry = torrent_info.file_at(i)
                content_type = content_types.get_content_type(file_entry.path)

                if content_type and content_type.startswith("video/"):
                    torrent.files[i] = File(
                        file_index=i,
                        torrent=torrent,
                    )

        return torrent

    def remove_torrent(self, info_hash: str):
        if info_hash in self.torrents:
            self.torrents.pop(info_hash)

    async def prepare_for_stream(
        self,
        info_hash: str,
        file_index: int,
        range_header: str | None = None,
    ) -> Stream:
        info_hash_sha1 = libtorrent.sha1_hash(bytes.fromhex(info_hash))
        torrent_handle = self.libtorrent_client_service.get_torrent_or_raise(
            info_hash_sha1
        )

        info_hash_str = str(torrent_handle.info_hash())
        torrent = self.torrents.get(info_hash_str)
        if not torrent:
            torrent = self.register_torrent(torrent_handle)

        torrent_file = torrent.get_file(file_index)
        if not torrent_file:
            raise HTTPException(
                404,
                f"A(z) {file_index} indexű fájl nem videó fájl vagy nem található a torrentben.",
            )

        # Metaadat lekérés indítása ha szükséges
        metadata_key = f"{info_hash}_{file_index}"
        if not torrent_file.metadata_probed:
            if metadata_key not in self._metadata_tasks:
                self._metadata_tasks[metadata_key] = asyncio.create_task(
                    self._probe_metadata_task(
                        file=torrent_file,
                    )
                )

            task = self._metadata_tasks.get(metadata_key)
            if task:
                await task

        parsed_range_header = self._parse_range_header(
            file_size=torrent_file.size,
            range_header=range_header,
        )

        stream = Stream(
            stream_id=uuid4().hex,
            torrent=torrent,
            file=torrent_file,
            stream_start_byte=parsed_range_header.start_byte,
            stream_end_byte=parsed_range_header.end_byte,
        )

        return stream

    async def stream(
        self,
        stream: Stream,
        request: Request,
    ) -> AsyncIterator[bytes]:
        # Stream regisztráció
        info_hash = stream.torrent.torrent_handle.info_hash()
        info_hash_str = str(info_hash)

        torrent = stream.torrent
        if info_hash_str in self.torrents:
            torrent = self.torrents[info_hash_str]
        else:
            self.torrents[info_hash_str] = torrent

        torrent_file = stream.file
        if torrent_file.file_index in torrent.files:
            torrent_file = torrent.files[torrent_file.file_index]
        else:
            torrent.files[torrent_file.file_index] = torrent_file

        if stream.id not in torrent_file.streams:
            stream.torrent = torrent
            stream.file = torrent_file
            torrent_file.streams[stream.id] = stream

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

                available_end_byte = self._check_piece_and_prioritize(
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
            self._end_stream(stream)

    async def _file_iterator(
        self,
        file_path: Path,
        start_byte: int,
        end_byte: int,
        request: Request,
    ) -> AsyncIterator[bytes]:
        with file_path.open("rb") as file_handle:
            file_handle.seek(start_byte)

            remaining = end_byte - start_byte + 1

            while remaining > 0:
                if await request.is_disconnected():
                    return

                chunk = file_handle.read(min(1024 * 1024, remaining))

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

        # A teljes file elérhetó, visszaadjuk az utolsó byte-ot.
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
            if set_piece_count > stream.file.prefetch_pieces:
                break

            piece_index = critical_piece_index + count_index
            if stream.torrent.torrent_handle.have_piece(piece_index):
                continue

            stream.torrent.torrent_handle.set_piece_deadline(
                piece_index, 1000 * set_piece_count
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
            stream.file.is_available = True
            piece_or_file_available.piece_available = True
            piece_or_file_available.file_available = True
            return piece_or_file_available

        stream_end_piece_index = min(
            stream.stream_end_piece_index,
            stream.stream_start_piece_index,
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

    async def _probe_metadata_task(
        self,
        file: File,
    ):
        try:
            metadata_pieces: set[int] = set()
            needed_metadata_pieces = math.ceil(
                METADATA_FETCH_SIZE / file.torrent.piece_size
            )
            metadata_pieces.update(
                range(
                    file.start_piece_index,
                    min(
                        file.start_piece_index + needed_metadata_pieces,
                        file.end_piece_index + 1,
                    ),
                )
            )
            metadata_pieces.update(
                range(
                    max(
                        file.start_piece_index,
                        file.end_piece_index - needed_metadata_pieces + 1,
                    ),
                    file.end_piece_index + 1,
                )
            )

            priorities = file.torrent.get_priorities()
            for metadata_piece in metadata_pieces:
                priorities[metadata_piece] = PRIO_7

            file.torrent.torrent_handle.prioritize_pieces(priorities)

            for metadata_piece in metadata_pieces:
                if not file.torrent.torrent_handle.have_piece(metadata_piece):
                    file.torrent.torrent_handle.set_piece_deadline(metadata_piece, 1000)

            while not all(
                file.torrent.torrent_handle.have_piece(metadata_piece)
                for metadata_piece in metadata_pieces
            ):
                await asyncio.sleep(0.5)

            ffprobe = FFmpeg(executable="ffprobe").input(  # type: ignore
                url=str(file.path),
                options={
                    "print_format": "json",
                    "show_format": None,
                    "show_streams": None,
                },
            )

            output = await ffprobe.execute()
            media = json.loads(output.decode("utf-8"))

            bitrate_raw = pydash.get(media, "format.bit_rate")
            if bitrate_raw is None:
                bitrate_raw = (
                    pydash.chain(media)
                    .get("streams", [])
                    .filter(lambda s: "bit_rate" in s)
                    .last()
                    .get("bit_rate")
                    .value()
                )

            bitrate: Optional[int] = None
            if bitrate_raw is not None:
                try:
                    bitrate = int(bitrate_raw)
                except (ValueError, TypeError):
                    bitrate = None

            if bitrate:
                piece_size = file.torrent.piece_size
                bytes_in_10_sec = (bitrate / 8) * 10
                pieces_in_10_sec = math.ceil(bytes_in_10_sec / piece_size)
                file.prefetch_pieces = pieces_in_10_sec
        except Exception as e:
            logger.error(
                f"Hiba történt a(z) {file.file_index} indexű torrent metadata elemzése közben: {e}"
            )
        finally:
            file.metadata_probed = True
            info_hash = str(file.torrent.torrent_handle.info_hash())
            metadata_key = f"{info_hash}_{file.file_index}"
            self._metadata_tasks.pop(metadata_key, None)

    def _end_stream(
        self,
        stream: Stream,
    ):
        file = stream.file
        file.streams.pop(stream.id, None)

        if not file.streams:
            self._end_stream_by_file(file)

    def _end_stream_by_file(self, file: File):
        torrent = file.torrent
        any_active_streams = any(file.streams for file in torrent.files.values())
        if not any_active_streams:
            torrent.torrent_handle.prioritize_pieces(torrent.default_priorities)
