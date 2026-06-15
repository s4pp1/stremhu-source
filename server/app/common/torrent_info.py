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
    files_count = torrent_info.num_files()

    files = []
    for index in range(files_count):
        file_entry = torrent_info.file_at(index)

        name = file_entry.path.split("/")[-1]
        offset = file_entry.offset
        size = file_entry.size

        start_piece_index = offset // piece_size
        end_piece_index = (offset + size - 1) // piece_size

        content_type = content_types.get_content_type(file_entry.path)

        files.append(
            TorrentFileInfo(
                name=name,
                path=file_entry.path,
                index=index,
                size=size,
                offset=offset,
                start_piece_index=start_piece_index,
                end_piece_index=end_piece_index,
                is_video=content_type.startswith("video/"),
            )
        )

    return TorrentInfo(
        info_hash=str(torrent_info.info_hash()),
        name=torrent_info.name(),
        size=torrent_info.total_size(),
        piece_size=piece_size,
        files=files,
    )
