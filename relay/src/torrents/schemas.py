from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class RelayTorrentState(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

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


class RelayTorrent(RelayTorrentState):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    name: str
    info_hash: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    total: int


class AddTorrent(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    torrent_file_path: str
    save_path: str = Field(
        ...,
        description="A torrents mappa abszolút elérési úrja.",
    )
    download_full_torrent: Optional[bool] = False


class PrioritizeAndWait(BaseModel):
    end_byte: Optional[int] = Field(...)


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
