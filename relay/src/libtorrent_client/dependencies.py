from functools import lru_cache

from libtorrent_client.service import LibtorrentClientService


@lru_cache
def get_libtorrent_client_service() -> LibtorrentClientService:
    return LibtorrentClientService()
