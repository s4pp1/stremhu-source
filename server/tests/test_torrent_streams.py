import uuid
from unittest.mock import MagicMock

import pytest

from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.torrent_streams.schemas import TorrentStream

# Torrent struktúrák teljes filmnézéssel, file listákkal
TEST_STREAMS = {
    "Superman.2025.2160p.MA.WEB-DL.DDP5.1.Atmos.H.265.HUN-FULCRUM": {
        "files": [
            TorrentFileInfo(
                name="fulcrum-superman.2025.2160p.web.ma.mkv",
                path="fulcrum-superman.2025.2160p.web.ma.mkv",
                size=25168000000,
                index=0,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            ),
            TorrentFileInfo(
                name="fulcrum-superman.2025.2160p.web.ma.nfo",
                path="fulcrum-superman.2025.2160p.web.ma.nfo",
                size=12000,
                index=1,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=False,
            ),
            TorrentFileInfo(
                name="fulcrum-superman.2025.2160p.web.ma.sfv",
                path="fulcrum-superman.2025.2160p.web.ma.sfv",
                size=49,
                index=2,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=False,
            ),
            TorrentFileInfo(
                name="fulcrum-superman.2025.2160p.web.ma-sample.mkv",
                path="Sample/fulcrum-superman.2025.2160p.web.ma-sample.mkv",
                size=200000000,
                index=3,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            ),
        ],
        "series": None,  # Film, nincs series
    },
    "The.Boondocks.S02.HUN.DVDRip.XviD-HSF": {
        "files": [
            TorrentFileInfo(
                name="hsf-bndcks-201.avi",
                path="hsf-bndcks-201.avi",
                size=183245000,
                index=0,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            ),
            TorrentFileInfo(
                name="hsf-bndcks-202.avi",
                path="hsf-bndcks-202.avi",
                size=186245000,
                index=1,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            ),
            TorrentFileInfo(
                name="hsf-bndcks-203.avi",
                path="hsf-bndcks-203.avi",
                size=183234000,
                index=2,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            ),
        ],
        "series": {
            "season": 2,
            "episode": 2,
            "imdb_id": "tt0427356",
            "tvdb_id": 12345,
            "tmdb_id": 12345,
            "name": "The Boondocks",
        },
    },
}


@pytest.mark.parametrize("torrent_name, details", TEST_STREAMS.items())
def test_from_imdb_id_snapshots(torrent_name, details, snapshot, monkeypatch):
    from app.modules.indexer_accounts.models import IndexerAccountModel

    # Fixáljuk a random UUID-t és token generálást, hogy determinisztikus legyen a teszt
    monkeypatch.setattr(
        "app.modules.torrent_streams.schemas.generate_stream_token",
        lambda *args, **kwargs: "mocked-token",
    )
    monkeypatch.setattr(uuid, "uuid4", lambda: "mocked-uuid")

    # Mock IndexerTorrent
    import datetime

    fixed_date = datetime.datetime(2026, 6, 9, 17, 39, 59, 552543)
    from app.modules.indexer_definitions.models import IndexerDefinitionModel

    indexer_definition = IndexerDefinitionModel(
        id="test_indexer",
        name="Test Indexer",
        url="http://test_indexer",
        details_path="/details",
    )
    indexer_account = IndexerAccountModel(
        indexer_id="test_indexer", username="test_user", password="test_password"
    )
    indexer_account.indexer_definition = indexer_definition
    indexer_account.created_at = fixed_date
    indexer_account.updated_at = fixed_date

    mock_indexer_torrent = MagicMock()
    mock_indexer_torrent.indexer_account = indexer_account
    mock_indexer_torrent.fallback_attributes = []
    mock_indexer_torrent.imdb_id = "tt1234567"
    mock_indexer_torrent.seeders = 150

    # Mock TorrentFileModel
    mock_torrent_file = MagicMock()
    mock_torrent_file.torrent_id = "test_torrent_id"
    mock_torrent_file.info_hash = "abcdef123456"
    mock_torrent_file.is_persisted = False
    mock_torrent_file.info = TorrentInfo(
        name=torrent_name,
        files=details["files"],
        info_hash="abcdef123456",
        size=25368012049,
        piece_size=1048576,
    )

    # Mock UserModel
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.api_key = "test-api-key"

    # Parse SeriesInfo if present
    from app.common.schemas.internal import SeriesInfo

    series_info = SeriesInfo(**details["series"]) if details["series"] else None

    stream = TorrentStream.from_imdb_id(
        indexer_torrent=mock_indexer_torrent,
        torrent_file=mock_torrent_file,
        app_url="http://test",
        user=mock_user,
        series=series_info,
    )

    assert stream is not None
    dump = stream.model_dump()

    # A mocked_indexer_account serialization removes functions, but just to be safe we extract the attributes we want to check
    assert dump == snapshot
