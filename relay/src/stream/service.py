from typing import Dict, List, Tuple

from torrents.constants import (
    EXTRA_PIECE_COUNT,
    PREFETCH_HIGH_PIECES,
    PREFETCH_MEDIUM_PIECES,
    PREFETCH_PIECES,
    PRIO_HIGH,
    PRIO_MEDIUM,
    PRIO_NORMAL,
    PRIO_SKIP,
)
from torrents.models.stream_piece import StreamPiece
from torrents.models.torrent import Torrent


class StreamService:
    def __init__(
        self,
    ):
        self.torrents: Dict[str, Torrent] = {}

    def get_or_raise(
        self,
        info_hash: str,
    ) -> Torrent:
        if info_hash not in self.torrents:
            raise KeyError(f'A(z) "{info_hash}" nem létezik.')
        return self.torrents[info_hash]

    def create_or_raise(
        self,
        info_hash: str,
        priorities: List[int],
        priority: int,
    ):
        if info_hash in self.torrents:
            raise KeyError(f'A(z) "{info_hash}" már létezik.')

        default_priorities = priorities.copy()

        for index in range(len(default_priorities)):
            default_priorities[index] = priority

        torrent = Torrent(
            current_priorities=default_priorities,
            default_priorities=default_priorities,
        )
        self.torrents[info_hash] = torrent

        return self.get_or_raise(info_hash)

    def remove(
        self,
        info_hash: str,
    ):
        self.torrents.pop(info_hash)

    def start_stream(
        self,
        info_hash: str,
        file_index: int,
        file_start_piece_index: int,
        file_end_piece_index: int,
        stream_id: str,
    ):
        torrent = self.get_or_raise(info_hash)

        file = torrent.get_or_create_file(
            file_index=file_index,
            start_piece_index=file_start_piece_index,
            end_piece_index=file_end_piece_index,
        )

        if not file.streams:
            priorities = torrent.default_priorities.copy()
            for priority_index in range(len(priorities)):
                priorities[priority_index] = PRIO_SKIP
            torrent.set_current_priorities(priorities)

        file.get_or_create_stream(
            stream_id=stream_id,
        )

    def set_streams_pieces(
        self,
        info_hash: str,
        file_index: int,
        stream_id: str,
        start_piece_index: int,
        end_piece_index: int,
    ) -> Tuple[int, int]:
        torrent = self.get_or_raise(info_hash)
        file = torrent.get_or_raise_file(file_index)
        stream = file.get_or_raise_stream(stream_id)

        stream_pieces: List[StreamPiece] = []

        for prefetch_index in range(PREFETCH_PIECES):
            priority_piece_index = (
                start_piece_index - EXTRA_PIECE_COUNT + prefetch_index
            )
            priority_end_piece_index = min(
                end_piece_index + EXTRA_PIECE_COUNT, file.end_piece_index
            )

            if priority_piece_index > priority_end_piece_index:
                break

            stream_piece = StreamPiece(
                piece_index=priority_piece_index,
                piece_priority=PRIO_NORMAL,
            )

            if PREFETCH_HIGH_PIECES > prefetch_index:
                stream_piece.piece_priority = PRIO_HIGH

            elif PREFETCH_MEDIUM_PIECES > prefetch_index:
                stream_piece.piece_priority = PRIO_MEDIUM

            stream_pieces.append(stream_piece)

        stream.set_stream_pieces(stream_pieces)

        return stream_pieces[0].piece_index, len(stream_pieces)

    def get_priorities_by_streams(
        self,
        info_hash: str,
    ) -> List[int]:
        torrent = self.get_or_raise(info_hash)

        all_stream_pieces: Dict[int, int] = {}

        for file_index in torrent.files:
            file = torrent.files[file_index]

            for stream_index in file.streams:
                stream = file.streams[stream_index]

                for stream in stream.stream_pieces:
                    piece_priority = all_stream_pieces.get(stream.piece_index)
                    if piece_priority is None or stream.piece_priority > piece_priority:
                        all_stream_pieces[stream.piece_index] = stream.piece_priority

        updated_priorities = torrent.current_priorities.copy()

        for priority_index in range(len(updated_priorities)):
            stream_priority = all_stream_pieces.get(priority_index)

            if not stream_priority:
                stream_priority = PRIO_SKIP

            updated_priorities[priority_index] = stream_priority

        torrent.set_current_priorities(updated_priorities)

        return updated_priorities

    def end_stream(
        self,
        info_hash: str,
        file_index: int,
        stream_id: str,
    ) -> List[int]:
        torrent = self.get_or_raise(info_hash)
        file = torrent.get_file(file_index)

        if file and file.streams:
            file.streams.pop(stream_id, None)
            torrent.files.pop(file_index, None)

        if not torrent.files:
            return torrent.default_priorities

        return self.get_priorities_by_streams(info_hash)
