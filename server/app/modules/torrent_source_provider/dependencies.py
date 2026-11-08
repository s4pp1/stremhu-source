from app.modules.indexers.dependencies import get_indexer_search_service
from app.modules.torrent_files.dependencies import create_isolated_torrent_files_service
from app.modules.torrent_source_provider.service import TorrentSourceProviderService


def create_torrent_source_provider_service() -> TorrentSourceProviderService:
    # Request-független: a megosztott keresés nem kap request Sessiont.
    return TorrentSourceProviderService(
        indexers_service=get_indexer_search_service(),
        isolated_torrent_files_service=create_isolated_torrent_files_service(),
    )
