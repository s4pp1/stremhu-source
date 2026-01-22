from functools import lru_cache

from libtorrent.service import LibtorrentService


@lru_cache
def get_libtorrent_service() -> LibtorrentService:
    return LibtorrentService()
