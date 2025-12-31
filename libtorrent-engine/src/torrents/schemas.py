from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .constants import PRIO_HIGH


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


class PiecesRangeAvailable(BaseModel):
    ready: bool
    is_available: bool = Field(
        ..., description="A fájl már teljesen le van töltve, csak a stream-elni kell."
    )


class PiecesRangeRequest(BaseModel):
    start_byte: int = Field(..., ge=0)
    end_byte: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_range(self) -> "PiecesRangeRequest":
        if self.end_byte < self.start_byte:
            raise ValueError("end_byte nagyobb kell legyen mint a start_byte")
        return self


class PrioritizeTorrentFile(BaseModel):
    priority: int = PRIO_HIGH
    start_byte: int
    end_byte: int


class RemoveTorrent(BaseModel):
    deleteFiles: bool = False
