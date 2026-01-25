from typing import List

import libtorrent as libtorrent
from fastapi import APIRouter, Depends
from torrents.dependencies import get_torrents_service
from torrents.schemas import (
    AddTorrent,
    RelayTorrent,
    RelayTorrentState,
)
from torrents.service import TorrentsService

router = APIRouter(
    prefix="/torrents",
    tags=["Torrents"],
)


@router.post(
    "/",
    response_model=RelayTorrent,
    operation_id="add_torrent",
)
def add_torrent(
    req: AddTorrent,
    torrents_service: TorrentsService = Depends(get_torrents_service),
):
    return torrents_service.add_torrent(req)


@router.get(
    "/",
    response_model=List[RelayTorrent],
    operation_id="get_torrents",
)
def get_torrents(
    torrents_service: TorrentsService = Depends(get_torrents_service),
):
    return torrents_service.get_torrents()


@router.get(
    "/{info_hash}",
    response_model=RelayTorrent,
    operation_id="get_torrent",
)
def get_torrent(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
):
    return torrents_service.get_torrent_or_raise(info_hash)


@router.get(
    "/{info_hash}/verification",
    response_model=RelayTorrentState,
    operation_id="get_torrent_state",
)
def get_torrent_state(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
):
    parsed_info_hash = torrents_service.parse_info_hash(info_hash)
    return torrents_service.get_torrent_state(parsed_info_hash)


@router.delete(
    "/{info_hash}",
    response_model=RelayTorrent,
    operation_id="delete_torrent",
)
def delete_torrent(
    info_hash: str,
    torrents_service: TorrentsService = Depends(get_torrents_service),
):
    return torrents_service.remove_torrent(
        info_hash=info_hash,
    )
