from functools import lru_cache

from fastapi import Depends
from libtorrent_client.service import LibtorrentClientService
from stream.dependencies import get_libtorrent_client_service
from torrents.service import TorrentsService


@lru_cache
def get_torrents_service(
    libtorrent_client_service: LibtorrentClientService = Depends(
        get_libtorrent_client_service
    ),
) -> TorrentsService:
    return TorrentsService(
        libtorrent_client_service=libtorrent_client_service,
    )
