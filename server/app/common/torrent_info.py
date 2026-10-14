import content_types
import libtorrent as libtorrent
from pydantic import BaseModel


class TorrentFileInfo(BaseModel):
    name: str
    path: str
    index: int
    size: int
    offset: int
    start_piece_index: int
    end_piece_index: int
    is_video: bool


class TorrentInfo(BaseModel):
    info_hash: str
    name: str
    size: int
    piece_size: int
    files: list[TorrentFileInfo]


def parse_torrent_info(torrent: bytes | libtorrent.torrent_info) -> TorrentInfo:
    """Parses raw .torrent bytes or a libtorrent.torrent_info object into a shared TorrentInfo structure."""
    if isinstance(torrent, bytes):
        torrent_info = libtorrent.torrent_info(torrent)
    else:
        torrent_info = torrent

    piece_size = torrent_info.piece_length()
    file_storage = torrent_info.layout()
    files_count = file_storage.num_files()

    files = []
    for index in range(files_count):
        file_path = file_storage.file_path(index)
        name = file_storage.file_name(index)
        offset = file_storage.file_offset(index)
        size = file_storage.file_size(index)

        start_piece_index = offset // piece_size
        end_piece_index = (offset + size - 1) // piece_size

        content_type = content_types.get_content_type(file_path)

        files.append(
            TorrentFileInfo(
                name=name,
                path=file_path,
                index=index,
                size=size,
                offset=offset,
                start_piece_index=start_piece_index,
                end_piece_index=end_piece_index,
                is_video=content_type is not None and content_type.startswith("video/"),
            )
        )

    return TorrentInfo(
        info_hash=str(torrent_info.info_hash()),
        name=torrent_info.name(),
        size=torrent_info.total_size(),
        piece_size=piece_size,
        files=files,
    )
