from typing import List, NamedTuple, Optional

from pydantic import BaseModel, Field


class UpdateSettings(BaseModel):
    download_rate_limit: Optional[int] = None
    upload_rate_limit: Optional[int] = None
    port: Optional[int] = None


class Torrent(BaseModel):
    name: str
    info_hash: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    progress: float
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


class PieceWindow(NamedTuple):
    start_piece_index: int
    end_piece_index: int
    priorities: List[int]
