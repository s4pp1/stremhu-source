from typing import Optional

from pydantic import BaseModel, Field


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
    end_byte: int


class PrioritizeAndWait(BaseModel):
    end_byte: Optional[int] = Field(...)


class RemoveTorrent(BaseModel):
    deleteFiles: bool = False


class StreamPiece(BaseModel):
    piece_index: int
    piece_priority: int


class PieceOrFileAvailable(BaseModel):
    piece_available: bool
    file_available: bool


class FileDetails(BaseModel):
    file_start_piece_index: int
    file_end_byte: int
    file_end_piece_index: int
    piece_size: int
    file_offset: int
    file_size: int
