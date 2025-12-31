from typing import List

import libtorrent as libtorrent
from fastapi import APIRouter

from .schemas import (
    AddTorrent,
    File,
    PiecesRangeAvailable,
    PiecesRangeRequest,
    PrioritizeTorrentFile,
    Torrent,
)
from .service import TorrentsService

router = APIRouter(
    prefix="/torrents",
    tags=["Torrents"],
)

torrents_service = TorrentsService()


@router.post(
    "/",
    response_model=Torrent,
    operation_id="add_torrent",
)
def add_torrent(req: AddTorrent):
    return torrents_service.add_torrent(req)


@router.get(
    "/",
    response_model=List[Torrent],
    operation_id="get_torrents",
)
def get_torrents():
    return torrents_service.get_torrents()


@router.get(
    "/{info_hash}",
    response_model=Torrent,
    operation_id="get_torrent",
)
def get_torrent(
    info_hash: str,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    return torrents_service.get_torrent_or_raise(parsed_info_hash)


@router.get(
    "/{info_hash}/files/{file_index}",
    response_model=File,
    operation_id="get_torrent_file",
)
def get_torrent_file(
    info_hash: str,
    file_index: int,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    return torrents_service.get_torrent_file(parsed_info_hash, file_index)


@router.post(
    "/{info_hash}/files/{file_index}/prioritize",
    operation_id="prioritize_pieces_range",
)
def prioritize_pieces_range(
    info_hash: str,
    file_index: int,
    req: PrioritizeTorrentFile,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    torrents_service.prioritize_pieces_range(parsed_info_hash, file_index, req)


@router.post(
    "/{info_hash}/files/{file_index}/pieces/priorities/reset",
    operation_id="reset_pieces_priorities",
)
def reset_pieces_priorities(
    info_hash: str,
    file_index: int,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    torrents_service.reset_pieces_priorities(parsed_info_hash, file_index)


@router.post(
    "/{info_hash}/files/{file_index}/pieces/available/check",
    response_model=PiecesRangeAvailable,
    operation_id="check_pieces_range_available",
)
def check_pieces_range_available(
    info_hash: str,
    file_index: int,
    req: PiecesRangeRequest,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    return torrents_service.check_pieces_range_available(
        info_hash=parsed_info_hash,
        file_index=file_index,
        start_byte=req.start_byte,
        end_byte=req.end_byte,
    )


@router.delete(
    "/{info_hash}",
    response_model=Torrent,
    operation_id="delete_torrent",
)
def delete_torrent(
    info_hash: str,
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    return torrents_service.remove_torrent(parsed_info_hash)
