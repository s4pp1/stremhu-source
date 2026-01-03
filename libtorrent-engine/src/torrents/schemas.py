from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from torrents.constants import (
    PREFETCH_HIGH_PIECES,
    PREFETCH_MEDIUM_PIECES,
    PREFETCH_PIECES,
    PRIO_HIGH,
    PRIO_MEDIUM,
    PRIO_NORMAL,
    PRIO_SKIP,
)


class UpdateSettings(BaseModel):
    download_rate_limit: Optional[int] = None
    upload_rate_limit: Optional[int] = None
    port: Optional[int] = None
    peer_limit: Optional[int] = None


class TorrentState(BaseModel):
    state: int = Field(
        ...,
        description=(
            "checking_files=1, downloading_metadata=2, downloading=3, finished=4, "
            "seeding=5, unused_enum_for_backwards_compatibility_allocating=6, "
            "checking_resume_data=7 "
            "https://www.libtorrent.org/reference-Torrent_Status.html#torrent_status"
        ),
    )
    progress: float


class Torrent(TorrentState):
    name: str
    info_hash: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    total: int


class AddTorrent(BaseModel):
    torrent_file_path: str
    save_path: str = Field(..., description="A torrents mappa abszolút elérési úrja.")
    download_full_torrent: Optional[bool] = False


class File(BaseModel):
    info_hash: str
    file_index: int
    path: str
    piece_length: int
    size: int
    offset: int
    is_available: bool = Field(
        ..., description="A fájl már teljesen le van töltve, csak a stream-elni kell."
    )


class PrioritizeAndWaitRequest(BaseModel):
    start_byte: int


class PrioritizeAndWait(BaseModel):
    available_end_byte: int
    is_available: bool = Field(
        ..., description="A fájl már teljesen le van töltve, csak a stream-elni kell."
    )


class RemoveTorrent(BaseModel):
    deleteFiles: bool = False


class StreamPiece(BaseModel):
    piece_index: int
    piece_priority: int


class Stream(BaseModel):
    stream_pieces: List[StreamPiece] = []

    def set_stream_pieces(
        self,
        pieces: List[StreamPiece],
    ):
        self.stream_pieces = pieces
        return self.stream_pieces


class FileStatus(BaseModel):
    start_piece_index: int
    end_piece_index: int
    streams: Dict[str, Stream] = {}

    def get_stream(
        self,
        stream_id: str,
    ) -> Stream | None:
        if stream_id not in self.streams:
            return None
        return self.streams[stream_id]

    def get_or_raise_stream(self, stream_id: str) -> Stream:
        stream = self.get_stream(stream_id)
        if not stream:
            raise KeyError(f'A(z) "{stream}" nem létezik.')
        return stream

    def get_or_create_stream(
        self,
        stream_id: str,
    ):
        stream = self.get_stream(stream_id)

        if stream:
            return stream

        stream = Stream()
        self.streams[stream_id] = stream
        return self.streams[stream_id]


class FileDetails(BaseModel):
    file_start_piece_index: int
    file_end_piece_index: int
    piece_size: int
    file_offset: int
    file_size: int


class TorrentStatus(BaseModel):
    file_statuses: Dict[int, FileStatus] = {}
    current_priorities: List[int]
    default_priorities: List[int]

    def get_file_status(
        self,
        file_index: int,
    ):
        if file_index not in self.file_statuses:
            return None
        return self.file_statuses[file_index]

    def get_or_raise_file_status(self, file_index: int) -> FileStatus:
        file_status = self.get_file_status(file_index)
        if not file_status:
            raise KeyError(f'A(z) "{file_index}" nem létezik.')
        return file_status

    def get_or_create_file_status(
        self,
        file_index: int,
        start_piece_index: int,
        end_piece_index: int,
    ):
        file_status = self.get_file_status(file_index)

        if file_status:
            return file_status

        file_status = FileStatus(
            start_piece_index=start_piece_index,
            end_piece_index=end_piece_index,
        )
        self.file_statuses[file_index] = file_status
        return self.file_statuses[file_index]

    def set_current_priorities(
        self,
        priorities: List[int],
    ) -> None:
        self.current_priorities = priorities


class TorrentStatuses(BaseModel):
    torrent_statuses: Dict[str, TorrentStatus] = {}

    def get_or_raise(
        self,
        info_hash: str,
    ) -> TorrentStatus:
        if info_hash not in self.torrent_statuses:
            raise KeyError(f'A(z) "{info_hash}" nem létezik.')
        return self.torrent_statuses[info_hash]

    def create_or_raise(
        self,
        info_hash: str,
        priorities: List[int],
        priority: int,
    ):
        if info_hash in self.torrent_statuses:
            raise KeyError(f'A(z) "{info_hash}" már létezik.')

        default_priorities = priorities.copy()

        for index in range(len(default_priorities)):
            default_priorities[index] = priority

        torrent_status = TorrentStatus(
            default_priorities=default_priorities,
            current_priorities=default_priorities,
        )
        self.torrent_statuses[info_hash] = torrent_status

        return self.get_or_raise(info_hash)

    def remove(
        self,
        info_hash: str,
    ):
        self.torrent_statuses.pop(info_hash)

    def start_stream(
        self,
        info_hash: str,
        file_index: int,
        file_start_piece_index: int,
        file_end_piece_index: int,
        stream_id: str,
    ):
        torrent_status = self.get_or_raise(info_hash)

        file_status = torrent_status.get_or_create_file_status(
            file_index=file_index,
            start_piece_index=file_start_piece_index,
            end_piece_index=file_end_piece_index,
        )

        if not file_status.streams:
            priorities = torrent_status.default_priorities.copy()
            for priority_index in range(len(priorities)):
                priorities[priority_index] = PRIO_SKIP
            torrent_status.set_current_priorities(priorities)

        file_status.get_or_create_stream(
            stream_id=stream_id,
        )

    def set_streams_pieces(
        self,
        info_hash: str,
        file_index: int,
        stream_id: str,
        start_piece_index: int,
    ) -> List[StreamPiece]:
        torrent_status = self.get_or_raise(info_hash)
        file_status = torrent_status.get_or_raise_file_status(file_index)
        stream = file_status.get_or_raise_stream(stream_id)

        stream_pieces: List[StreamPiece] = []

        for prefetch_index in range(PREFETCH_PIECES):
            piece_index = start_piece_index + prefetch_index

            if piece_index > file_status.end_piece_index:
                break

            stream_piece = StreamPiece(
                piece_index=piece_index,
                piece_priority=PRIO_NORMAL,
            )

            if PREFETCH_HIGH_PIECES > prefetch_index:
                stream_piece.piece_priority = PRIO_HIGH

            elif PREFETCH_MEDIUM_PIECES > prefetch_index:
                stream_piece.piece_priority = PRIO_MEDIUM

            stream_pieces.append(stream_piece)

        stream.set_stream_pieces(stream_pieces)

        return stream_pieces[:4]

    def get_priorities_by_streams(
        self,
        info_hash: str,
    ) -> List[int]:
        torrent_status = self.get_or_raise(info_hash)

        all_stream_pieces: Dict[int, int] = {}

        for file_status_index in torrent_status.file_statuses:
            file_status = torrent_status.file_statuses[file_status_index]

            for stream_index in file_status.streams:
                stream = file_status.streams[stream_index]

                for stream in stream.stream_pieces:
                    piece = all_stream_pieces.get(stream.piece_index)
                    if piece is None or stream.piece_priority > piece:
                        all_stream_pieces[stream.piece_index] = stream.piece_priority

        updated_priorities = torrent_status.current_priorities.copy()

        for priority_index in range(len(updated_priorities)):
            stream_priority = all_stream_pieces.get(priority_index)

            if not stream_priority:
                stream_priority = PRIO_SKIP

            updated_priorities[priority_index] = stream_priority

        torrent_status.set_current_priorities(updated_priorities)

        return updated_priorities

    def end_stream(
        self,
        info_hash: str,
        file_index: int,
        stream_id: str,
    ) -> List[int]:
        torrent_status = self.get_or_raise(info_hash)
        file_status = torrent_status.get_or_raise_file_status(file_index)
        file_status.streams.pop(stream_id)

        if not file_status.streams:
            torrent_status.file_statuses.pop(file_index)

        if not torrent_status.file_statuses:
            return torrent_status.default_priorities

        return self.get_priorities_by_streams(info_hash)
