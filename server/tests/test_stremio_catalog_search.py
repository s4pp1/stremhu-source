from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.stremio.catalogs_service import StremioCatalogsService
from app.modules.stremio.dependencies import get_stremio_catalogs_service
from app.modules.stremio.enums import ContentType, MediaType, StreamIdType
from app.modules.stremio.schemas import (
    MetaDetail,
    ParsedExtra,
    TorrentStreamId,
)
from app.modules.stremio.utils import parse_stream_id
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileSnapshot
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrent_source_provider.schemas import TorrentSource
from app.modules.torrent_source_provider.service import TorrentSourceProviderService
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.users.models import UserModel
from tests.helpers import make_account_ref


@pytest.fixture
def mock_torrent_file():
    info = TorrentInfo(
        info_hash="abc123hash",
        name="Lupin.S04.1080p.NF.WEB-DL.DDP5.1.Atmos",
        size=4000000000,
        piece_size=1048576,
        files=[
            TorrentFileInfo(
                name="Lupin.S04E01.1080p.mkv",
                path="Lupin S04/Lupin.S04E01.1080p.mkv",
                index=0,
                size=2000000000,
                offset=0,
                start_piece_index=0,
                end_piece_index=1907,
                is_video=True,
            ),
            TorrentFileInfo(
                name="Lupin.S04E02.1080p.mkv",
                path="Lupin S04/Lupin.S04E02.1080p.mkv",
                index=1,
                size=2000000000,
                offset=2000000000,
                start_piece_index=1907,
                end_piece_index=3814,
                is_video=True,
            ),
            TorrentFileInfo(
                name="sample.mkv",
                path="Lupin S04/Sample/sample.mkv",
                index=2,
                size=50000000,
                offset=4000000000,
                start_piece_index=3814,
                end_piece_index=3862,
                is_video=True,
            ),
        ],
    )
    import libtorrent

    torrent_bytes = libtorrent.bencode(
        {
            b"info": {
                b"name": b"x",
                b"piece length": 16384,
                b"pieces": b"\0" * 20,
                b"length": 1,
            }
        }
    )
    torrent_file = TorrentFileModel(
        indexer_id="ncore",
        torrent_id="999888",
        torrent_bytes=torrent_bytes,
    )
    torrent_file._cached_info = info
    torrent_file.info_hash = "abc123hash"
    return TorrentFileSnapshot.from_model(torrent_file)


@pytest.fixture
def mock_movie_torrent_file():
    info = TorrentInfo(
        info_hash="movie123hash",
        name="Arsene.Lupin.2004.BDRip.x264.HuN",
        size=2000000000,
        piece_size=1048576,
        files=[
            TorrentFileInfo(
                name="Arsene.Lupin.2004.mkv",
                path="Arsene.Lupin.2004.mkv",
                index=0,
                size=2000000000,
                offset=0,
                start_piece_index=0,
                end_piece_index=1907,
                is_video=True,
            ),
        ],
    )
    import libtorrent

    torrent_bytes = libtorrent.bencode(
        {
            b"info": {
                b"name": b"m",
                b"piece length": 16384,
                b"pieces": b"\0" * 20,
                b"length": 1,
            }
        }
    )
    torrent_file = TorrentFileModel(
        indexer_id="ncore",
        torrent_id="111222",
        torrent_bytes=torrent_bytes,
    )
    torrent_file._cached_info = info
    torrent_file.info_hash = "movie123hash"
    return TorrentFileSnapshot.from_model(torrent_file)


@pytest.mark.anyio
async def test_direct_query_catalog_search(mock_torrent_file, mock_movie_torrent_file):
    mock_files_service = MagicMock(spec=TorrentFilesService)
    mock_isolated_service = MagicMock(spec=IsolatedTorrentFilesService)
    mock_provider = AsyncMock(spec=TorrentSourceProviderService)

    mock_series_source = TorrentSource(
        indexer_torrent=IndexerTorrent(
            torrent_id="999888",
            download_url="https://ncore.invalid/dl",
            imdb_id="tt2531336",
            seeders=50,
            indexer_account=make_account_ref("ncore"),
        ),
        torrent_file=mock_torrent_file,
    )

    mock_movie_source = TorrentSource(
        indexer_torrent=IndexerTorrent(
            torrent_id="111222",
            download_url="https://ncore.invalid/dl2",
            imdb_id="tt0373690",
            seeders=30,
            indexer_account=make_account_ref("ncore"),
        ),
        torrent_file=mock_movie_torrent_file,
    )

    async def fake_find_by_query(query, media_type=None):
        if media_type == "movie":
            return [mock_movie_source], []
        elif media_type == "series":
            return [mock_series_source], []
        return [mock_series_source, mock_movie_source], []

    mock_provider.find_by_query.side_effect = fake_find_by_query

    service = StremioCatalogsService(
        torrent_files_service=mock_files_service,
        torrent_source_provider_service=mock_provider,
        isolated_torrent_files_service=mock_isolated_service,
    )

    # 1. Movie katalógus keresés
    res_movie = await service.get_catalog(
        media_type=MediaType.MOVIE,
        catalog_id="search",
        extra=ParsedExtra(search="Lupin"),
    )
    assert len(res_movie.metas) == 1
    assert res_movie.metas[0].name == mock_movie_torrent_file.info.name
    assert res_movie.metas[0].type == ContentType.MOVIE
    assert res_movie.metas[0].id == "stremhu-source:ncore:111222"
    assert res_movie.metas[0].imdb_id == "tt0373690"
    assert (
        res_movie.metas[0].poster
        == "https://images.metahub.space/poster/medium/tt0373690/img"
    )

    # 2. Series katalógus keresés
    res_series = await service.get_catalog(
        media_type=MediaType.SERIES,
        catalog_id="search",
        extra=ParsedExtra(search="Lupin"),
    )
    assert len(res_series.metas) == 1
    assert res_series.metas[0].name == mock_torrent_file.info.name
    assert res_series.metas[0].type == ContentType.SERIES
    assert res_series.metas[0].id == "stremhu-source:ncore:999888"
    assert res_series.metas[0].imdb_id == "tt2531336"
    assert (
        res_series.metas[0].poster
        == "https://images.metahub.space/poster/medium/tt2531336/img"
    )


@pytest.mark.anyio
async def test_series_parser_safeguard_filters_series_from_movie_catalog(
    mock_torrent_file, mock_movie_torrent_file
):
    mock_files_service = MagicMock(spec=TorrentFilesService)
    mock_isolated_service = MagicMock(spec=IsolatedTorrentFilesService)
    mock_provider = AsyncMock(spec=TorrentSourceProviderService)

    # Szimuláljuk, hogy a tracker tévesen sorozatot és filmet is visszaadott a movie keresésre
    mock_series_source = TorrentSource(
        indexer_torrent=IndexerTorrent(
            torrent_id="999888",
            download_url="https://ncore.invalid/dl",
            imdb_id="tt2531336",
            seeders=100,
            indexer_account=make_account_ref("ncore"),
        ),
        torrent_file=mock_torrent_file,
    )
    mock_movie_source = TorrentSource(
        indexer_torrent=IndexerTorrent(
            torrent_id="111222",
            download_url="https://ncore.invalid/dl2",
            imdb_id="tt0373690",
            seeders=10,
            indexer_account=make_account_ref("ncore"),
        ),
        torrent_file=mock_movie_torrent_file,
    )

    mock_provider.find_by_query.return_value = (
        [mock_series_source, mock_movie_source],
        [],
    )

    service = StremioCatalogsService(
        torrent_files_service=mock_files_service,
        torrent_source_provider_service=mock_provider,
        isolated_torrent_files_service=mock_isolated_service,
    )

    # Film keresésnél a SeriesParsernek ki kell szűrnie a Lupin.S04 sorozatot!
    res_movie = await service.get_catalog(
        media_type=MediaType.MOVIE,
        catalog_id="search",
        extra=ParsedExtra(search="Lupin"),
    )
    assert len(res_movie.metas) == 1
    assert res_movie.metas[0].id == "stremhu-source:ncore:111222"
    assert res_movie.metas[0].name == mock_movie_torrent_file.info.name


def test_meta_detail_series_generates_episodes(mock_torrent_file):
    meta_detail = MetaDetail.from_torrent_file(
        mock_torrent_file, content_type=ContentType.SERIES
    )

    assert meta_detail.type == ContentType.SERIES
    assert meta_detail.videos is not None
    # Csak az E01 és E02 kerül be, a sample.mkv ki van zárva
    assert len(meta_detail.videos) == 2

    v1 = meta_detail.videos[0]
    assert v1.season == 4
    assert v1.episode == 1
    assert v1.id == "stremhu-source:ncore:999888:0"

    v2 = meta_detail.videos[1]
    assert v2.season == 4
    assert v2.episode == 2
    assert v2.id == "stremhu-source:ncore:999888:1"

    assert meta_detail.behavior_hints is not None
    assert meta_detail.behavior_hints.default_video_id == "stremhu-source:ncore:999888:0"


def test_parse_stream_id_with_file_index():
    # Régi formátum (file_index nélkül)
    sid_old = parse_stream_id("stremhu-source:ncore:999888")
    assert isinstance(sid_old, TorrentStreamId)
    assert sid_old.type == StreamIdType.TORRENT
    assert sid_old.indexer_id == "ncore"
    assert sid_old.torrent_id == "999888"
    assert sid_old.file_index is None

    # Új formátum (file_index-szel)
    sid_new = parse_stream_id("stremhu-source:ncore:999888:1")
    assert isinstance(sid_new, TorrentStreamId)
    assert sid_new.indexer_id == "ncore"
    assert sid_new.torrent_id == "999888"
    assert sid_new.file_index == 1


def test_torrent_stream_filtering_by_file_index(mock_torrent_file):
    user = UserModel(id="u1", username="test")
    idx_torrent = IndexerTorrent(
        torrent_id="999888",
        download_url="https://ncore.invalid/dl",
        indexer_account=make_account_ref("ncore"),
    )

    # 1. Összes videofájl lekérése (file_index=None)
    all_streams = TorrentStream.from_torrent_id(
        indexer_torrent=idx_torrent,
        torrent_file=mock_torrent_file,
        app_url="http://localhost:7070",
        user=user,
        file_index=None,
    )
    assert len(all_streams) == 2  # E01 és E02

    # 2. Csak a 2. epizód lekérése (file_index=1)
    ep2_streams = TorrentStream.from_torrent_id(
        indexer_torrent=idx_torrent,
        torrent_file=mock_torrent_file,
        app_url="http://localhost:7070",
        user=user,
        file_index=1,
    )
    assert len(ep2_streams) == 1
    assert ep2_streams[0].file_name == "Lupin.S04E02.1080p.mkv"


def test_stremio_catalog_api_search_endpoint(mock_torrent_file):
    client = TestClient(app)
    mock_auth_service = AsyncMock(spec=AuthService)
    mock_auth_service.verify_api_key.return_value = UserModel(
        id="user123", username="testuser"
    )

    mock_catalogs_service = AsyncMock(spec=StremioCatalogsService)
    from app.modules.stremio.schemas import MetaPreview, StremioCatalogResponse

    mock_catalogs_service.get_catalog.return_value = StremioCatalogResponse(
        metas=[
            MetaPreview.from_torrent_file(
                mock_torrent_file, content_type=ContentType.SERIES
            )
        ]
    )

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_stremio_catalogs_service] = (
        lambda: mock_catalogs_service
    )

    try:
        resp = client.get(
            "/api/dummy_key/stremio/catalog/series/search/search=Lupin.json"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "metas" in data
        assert len(data["metas"]) == 1
        assert data["metas"][0]["name"] == mock_torrent_file.info.name
        assert data["metas"][0]["type"] == "series"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_catalog_disabled_for_user():
    mock_files_service = MagicMock(spec=TorrentFilesService)
    mock_isolated_service = MagicMock(spec=IsolatedTorrentFilesService)
    mock_provider = AsyncMock(spec=TorrentSourceProviderService)

    catalogs_service = StremioCatalogsService(
        torrent_files_service=mock_files_service,
        isolated_torrent_files_service=mock_isolated_service,
        torrent_source_provider_service=mock_provider,
    )

    user_disabled = UserModel(
        id="user_dis",
        username="disabled_user",
        enable_catalog_search=False,
    )

    # When enable_catalog_search is False, get_catalog returns empty metas without calling provider
    res = await catalogs_service.get_catalog(
        media_type=MediaType.SERIES,
        catalog_id="search",
        extra=ParsedExtra(search="Lupin"),
        user=user_disabled,
    )
    assert res.metas == []
    mock_provider.find_by_query.assert_not_called()


@pytest.mark.anyio
async def test_catalog_toggle_takes_effect_without_reinstalling_the_addon():
    # Stremio/Nuvio store the manifest at install time, so the manifest must not depend on the
    # toggle: installed while disabled, the client must still know the search catalog exists and
    # the server decides per request whether to answer it.
    from app.modules.settings.service import SettingsService
    from app.modules.stremio.enums import ShortManifestResource
    from app.modules.stremio.service import StremioService
    from app.modules.torrent_streams.service import TorrentStreamsService

    stremio_service = StremioService(
        torrent_streams_service=MagicMock(spec=TorrentStreamsService),
        settings_service=MagicMock(spec=SettingsService),
    )
    user = UserModel(id="user_toggle", username="toggle_user", enable_catalog_search=False)
    installed_manifest = stremio_service.manifest().model_dump(by_alias=True)
    assert ShortManifestResource.CATALOG in installed_manifest["resources"]
    assert [(c["type"], c["id"]) for c in installed_manifest["catalogs"]] == [
        (ContentType.MOVIE, "search"),
        (ContentType.SERIES, "search"),
    ]

    mock_provider = AsyncMock(spec=TorrentSourceProviderService)
    mock_provider.find_by_query.return_value = ([], [])
    catalogs_service = StremioCatalogsService(
        torrent_files_service=MagicMock(spec=TorrentFilesService),
        isolated_torrent_files_service=MagicMock(spec=IsolatedTorrentFilesService),
        torrent_source_provider_service=mock_provider,
    )
    search = ParsedExtra(search="Lupin")

    disabled = await catalogs_service.get_catalog(MediaType.SERIES, "search", search, user=user)
    assert disabled.metas == []
    mock_provider.find_by_query.assert_not_called()

    user.enable_catalog_search = True  # toggled in the web UI, the addon is NOT reinstalled
    assert stremio_service.manifest().model_dump(by_alias=True) == installed_manifest
    await catalogs_service.get_catalog(MediaType.SERIES, "search", search, user=user)
    mock_provider.find_by_query.assert_awaited_once()

