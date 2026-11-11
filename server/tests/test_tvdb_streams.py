from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.common.schemas.internal import SeriesInfo
from app.main import app
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.settings.service import SettingsService
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.enums import StreamIdType
from app.modules.stremio.schemas import KitsuStreamId, StremioStream, TvdbStreamId
from app.modules.stremio.service import StremioService
from app.modules.stremio.tvdb_resolver import TvdbResolver
from app.modules.stremio.utils import parse_stream_id
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.users.models import UserModel


def test_parse_tvdb_stream_id_with_season_and_episode():
    result = parse_stream_id("tvdb:348545:2:5")
    assert isinstance(result, TvdbStreamId)
    assert result.type == StreamIdType.TVDB
    assert result.tvdb_id == "348545"
    assert result.series_info is not None
    assert result.series_info.season == 2
    assert result.series_info.episode == 5


def test_parse_tvdb_stream_id_single_id():
    result = parse_stream_id("tvdb:348545")
    assert isinstance(result, TvdbStreamId)
    assert result.type == StreamIdType.TVDB
    assert result.tvdb_id == "348545"
    assert result.series_info is None


@pytest.mark.anyio
async def test_tvdb_resolver_caching():
    resolver = TvdbResolver()
    resolver._cache["12345"] = "tt9999999"

    # A gyorsítótárból azonnal vissza kell térnie
    res = await resolver.resolve_tvdb_to_imdb("12345")
    assert res == "tt9999999"


@pytest.mark.anyio
async def test_stremio_service_resolves_tvdb():
    mock_torrent_streams_service = AsyncMock(spec=TorrentStreamsService)
    mock_settings_service = AsyncMock(spec=SettingsService)
    mock_settings_service.get_app_url.return_value = "http://localhost:7070"

    mock_tvdb_resolver = AsyncMock(spec=TvdbResolver)
    mock_tvdb_resolver.resolve_tvdb_to_imdb.return_value = "tt9335498"
    mock_tvdb_resolver.get_title_by_imdb.return_value = "Demon Slayer"
    mock_tvdb_resolver.get_episode_mappings.return_value = ([], [])
    mock_tvdb_resolver.get_alternate_imdb_ids.return_value = []

    mock_torrent_streams_service.find_by_imdb.return_value = ([], [])

    service = StremioService(
        torrent_streams_service=mock_torrent_streams_service,
        settings_service=mock_settings_service,
        tvdb_resolver_service=mock_tvdb_resolver,
    )

    user = UserModel(id="user1", username="test")
    parsed_id = TvdbStreamId(
        tvdb_id="348545",
        series_info=SeriesInfo(season=1, episode=1),
    )

    streams = await service.get_streams(user=user, parsed_id=parsed_id)

    mock_tvdb_resolver.resolve_tvdb_to_imdb.assert_awaited_once_with("348545")
    assert mock_torrent_streams_service.find_by_imdb.await_count == 1
    call_kwargs = mock_torrent_streams_service.find_by_imdb.await_args.kwargs
    assert call_kwargs["imdb_id"] == "tt9335498"
    assert call_kwargs["series"] == SeriesInfo(season=1, episode=1)
    assert callable(call_kwargs["fallback_title"])
    # A lazy getter meghívásával a címlekérésnek le kell futnia
    assert await call_kwargs["fallback_title"]() == "Demon Slayer"
    mock_tvdb_resolver.get_title_by_imdb.assert_awaited_once_with(
        "tt9335498", is_series=True
    )
    assert streams == []


@pytest.mark.anyio
async def test_stremio_service_tvdb_resolution_failure():
    mock_torrent_streams_service = AsyncMock(spec=TorrentStreamsService)
    mock_settings_service = AsyncMock(spec=SettingsService)
    mock_settings_service.get_app_url.return_value = "http://localhost:7070"

    mock_tvdb_resolver = AsyncMock(spec=TvdbResolver)
    mock_tvdb_resolver.resolve_tvdb_to_imdb.return_value = None

    service = StremioService(
        torrent_streams_service=mock_torrent_streams_service,
        settings_service=mock_settings_service,
        tvdb_resolver_service=mock_tvdb_resolver,
    )

    user = UserModel(id="user1", username="test")
    parsed_id = TvdbStreamId(
        tvdb_id="999999",
        series_info=None,
    )

    streams = await service.get_streams(user=user, parsed_id=parsed_id)
    assert len(streams) == 1
    assert "TVDB feloldási hiba" in streams[0].name


def test_tvdb_stream_api_endpoint():
    client = TestClient(app)
    mock_stremio_service = AsyncMock(spec=StremioService)
    mock_stremio_service.get_streams.return_value = [
        StremioStream(
            name="Demon Slayer Stream",
            description="1080p stream",
            url="http://localhost/play",
        )
    ]

    mock_auth_service = AsyncMock(spec=AuthService)
    mock_auth_service.verify_api_key.return_value = UserModel(
        id="user123", username="testuser"
    )

    app.dependency_overrides[get_stremio_service] = lambda: mock_stremio_service
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    try:
        response = client.get(
            "/api/dummy_api_key/stremio/stream/series/tvdb:348545:1:1.json"
        )
        assert response.status_code == 200
        data = response.json()
        assert "streams" in data
        assert len(data["streams"]) == 1
        assert data["streams"][0]["name"] == "Demon Slayer Stream"
    finally:
        app.dependency_overrides.clear()


def test_parse_kitsu_stream_id():
    result = parse_stream_id("kitsu:41370:1")
    assert isinstance(result, KitsuStreamId)
    assert result.type == StreamIdType.KITSU
    assert result.kitsu_id == "41370"
    assert result.episode == 1
    assert result.series_info is not None
    assert result.series_info.episode == 1


@pytest.mark.anyio
async def test_kitsu_resolver_caching():
    resolver = TvdbResolver()
    resolver._cache["kitsu_41370_1"] = ("tt9335498", 1, 1)

    res = await resolver.resolve_kitsu_to_imdb("41370", 1)
    assert res == ("tt9335498", 1, 1)


def test_anime_series_parser_cases():
    from app.modules.torrent_streams.utils.series_parser import SeriesParser

    # Naruto 3-jegyű számok
    s, e = SeriesParser("Naruto - 105.mkv").parse()
    assert s == []
    assert e == [105]

    s, e = SeriesParser("Naruto Shippuden - 215 [1080p].mkv").parse()
    assert s == []
    assert e == [215]

    # Attack on Titan Final Season & Arc
    s, e = SeriesParser("[Erai-raws] Shingeki no Kyojin The Final Season - 01 [1080p].mkv").parse()
    assert s == [4]
    assert e == [1]

    s, e = SeriesParser("Attack.on.Titan.S04E17.1080p.mkv").parse()
    assert s == [4]
    assert e == [17]

    # Demon Slayer Arcs (arc nevek nincsenek beleégetve, epizódszámokat generikusan bontja ki)
    s, e = SeriesParser("[SubsPlease] Kimetsu no Yaiba - Hashira Geiko-hen - 01 (1080p).mkv").parse()
    assert s == []
    assert e == [1]

    s, e = SeriesParser("Kimetsu no Yaiba - Yuukaku-hen 01.mkv").parse()
    assert s == []
    assert e == [1]

    s, e = SeriesParser("Demon.Slayer.Mugen.Train.Arc.E01.1080p.mkv").parse()
    assert s == []
    assert e == [1]


def test_anime_stream_file_resolver_matching():
    from app.common.torrent_info import TorrentFileInfo, TorrentInfo
    from app.modules.torrent_streams.utils.stream_file_resolver import (
        StreamFileResolver,
    )

    def make_file(name: str, index: int) -> TorrentFileInfo:
        return TorrentFileInfo(
            name=name,
            path=name,
            size=1000,
            offset=index * 1000,
            start_piece_index=index,
            end_piece_index=index,
            is_video=True,
            index=index,
        )

    # Demon Slayer S2E8 (Yuukaku ep 1)
    t_info_ds = TorrentInfo(
        info_hash="hash_ds",
        name="Kimetsu no Yaiba Yuukaku-hen",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Kimetsu no Yaiba - Yuukaku-hen - 01.mkv", 0),
            make_file("Kimetsu no Yaiba - Yuukaku-hen - 02.mkv", 1),
        ],
    )
    res_ds = StreamFileResolver(
        t_info_ds,
        series=SeriesInfo(season=2, episode=8, alternate_episodes=[1]),
    ).resolve()
    assert res_ds is not None
    assert res_ds.name == "Kimetsu no Yaiba - Yuukaku-hen - 01.mkv"

    # Attack on Titan S4E16 (abszolút ep 75)
    t_info_aot = TorrentInfo(
        info_hash="hash_aot",
        name="Shingeki no Kyojin Pack",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Shingeki no Kyojin - 74.mkv", 0),
            make_file("Shingeki no Kyojin - 75.mkv", 1),
        ],
    )
    res_aot = StreamFileResolver(
        t_info_aot,
        series=SeriesInfo(season=4, episode=16, alternate_episodes=[75]),
    ).resolve()
    assert res_aot is not None
    assert res_aot.name == "Shingeki no Kyojin - 75.mkv"

    # Naruto S1E5: nem keveri össze a 105. résszel!
    t_info_naruto = TorrentInfo(
        info_hash="hash_naruto",
        name="Naruto Pack",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Naruto - 005.mkv", 0),
            make_file("Naruto - 105.mkv", 1),
        ],
    )
    res_naruto = StreamFileResolver(t_info_naruto, series=SeriesInfo(season=1, episode=5)).resolve()
    assert res_naruto is not None
    assert res_naruto.name == "Naruto - 005.mkv"


@pytest.mark.anyio
async def test_find_by_imdb_fallback_to_title_search():
    from unittest.mock import MagicMock

    from app.modules.preferences.service import PreferencesService
    from app.modules.torrent_source_provider.service import TorrentSourceProviderService

    mock_provider = AsyncMock(spec=TorrentSourceProviderService)
    # IMDb keresésre 0 találat
    mock_provider.find_by_imdb_id.return_value = ([], [])
    # Név szerinti keresésre van találat
    mock_source = MagicMock()
    mock_source.indexer_torrent.indexer_account.indexer_id = "ncore"
    mock_source.indexer_torrent.torrent_id = "1"
    mock_provider.find_by_query.return_value = ([mock_source], [])

    mock_settings = AsyncMock(spec=SettingsService)
    mock_settings.get_app_url.return_value = "http://localhost:7070"

    mock_preferences = MagicMock(spec=PreferencesService)
    mock_preferences.get_list.return_value = []

    mock_torrents = MagicMock()
    mock_torrents.get_torrents.return_value = []

    service = TorrentStreamsService(
        db=AsyncMock(),
        torrent_source_provider_service=mock_provider,
        torrents_service=mock_torrents,
        settings_service=mock_settings,
        preferences_service=mock_preferences,
    )

    user = UserModel(id="user1", username="test", enable_smart_filter=False)
    await service.find_by_imdb(
        user=user,
        imdb_id="tt9335498",
        series=SeriesInfo(season=1, episode=1),
        fallback_title="Demon Slayer: Kimetsu no Yaiba",
    )

    mock_provider.find_by_imdb_id.assert_awaited_once_with("tt9335498")
    mock_provider.find_by_query.assert_awaited_once_with("Demon Slayer S01")


def test_one_piece_series_parser_and_resolver():
    from app.common.torrent_info import TorrentFileInfo, TorrentInfo
    from app.modules.torrent_streams.utils.series_parser import SeriesParser
    from app.modules.torrent_streams.utils.stream_file_resolver import (
        StreamFileResolver,
    )

    # 1. SeriesParser generikus tesztek
    p1 = SeriesParser("[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv")
    s, e = p1.parse()
    assert e == [1089]

    p2 = SeriesParser("One Piece - Wano Kuni - 892.mkv")
    s, e = p2.parse()
    assert e == [892]

    p3 = SeriesParser("One Piece - Egghead Arc - 1089.mkv")
    s, e = p3.parse()
    assert e == [1089]

    p4 = SeriesParser("One Piece 890-895.mkv")
    s, e = p4.parse()
    assert e == [890, 891, 892, 893, 894, 895]

    def make_file(name: str, index: int) -> TorrentFileInfo:
        return TorrentFileInfo(
            name=name,
            path=name,
            size=1000,
            offset=index * 1000,
            start_piece_index=index,
            end_piece_index=index,
            is_video=True,
            index=index,
        )

    # 2. Generikus feloldás: S21E01 kérés alternate_episodes=[892]-vel feloldja a "One Piece - 892.mkv" fájlt
    t_info_op1 = TorrentInfo(
        info_hash="hash_op1",
        name="One Piece Batch",
        size=3000,
        piece_size=1000,
        files=[
            make_file("One Piece - 891.mkv", 0),
            make_file("One Piece - 892.mkv", 1),
            make_file("One Piece - 893.mkv", 2),
        ],
    )
    res_cinemeta = StreamFileResolver(
        t_info_op1,
        series=SeriesInfo(season=21, episode=1, alternate_episodes=[892]),
    ).resolve()
    assert res_cinemeta is not None
    assert res_cinemeta.name == "One Piece - 892.mkv"

    # 3. S22E04 kérés alternate_episodes=[1089]-vel feloldja az 1089. részt
    t_info_op2 = TorrentInfo(
        info_hash="hash_op2",
        name="[SubsPlease] One Piece - 1089 (1080p)",
        size=1000,
        piece_size=1000,
        files=[
            make_file("[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv", 0),
        ],
    )
    res_egghead = StreamFileResolver(
        t_info_op2,
        series=SeriesInfo(season=22, episode=4, alternate_episodes=[1089]),
    ).resolve()
    assert res_egghead is not None
    assert res_egghead.name == "[SubsPlease] One Piece - 1089 (1080p) [98E7B28B].mkv"

    # 4. Kitsu kérés S1 E892 feloldja a "One Piece - 892.mkv"-t ÉS a "One.Piece.S21E01.mkv"-t is
    t_info_op_season_name = TorrentInfo(
        info_hash="hash_op3",
        name="One Piece Season 21",
        size=2000,
        piece_size=1000,
        files=[
            make_file("One.Piece.S21E01.1080p.mkv", 0),
            make_file("One.Piece.S21E02.1080p.mkv", 1),
        ],
    )
    res_kitsu_mapped = StreamFileResolver(
        t_info_op_season_name,
        series=SeriesInfo(
            season=1,
            episode=892,
            alternate_seasons=[21],
            alternate_episodes=[1],
        ),
    ).resolve()
    assert res_kitsu_mapped is not None
    assert res_kitsu_mapped.name == "One.Piece.S21E01.1080p.mkv"

    # 5. One Piece S2E1 (Cinemeta) -> feloldás S01-nek elnevezett HorribleSubs pakkból (abszolút 9. rész)
    t_info_op_s01_pack = TorrentInfo(
        info_hash="hash_op_s1",
        name="One Piece S01 480p",
        size=5000,
        piece_size=1000,
        files=[
            make_file("One Piece S01 480p/[HorribleSubs] One Piece - 01 [480p].mkv", 0),
            make_file("One Piece S01 480p/[HorribleSubs] One Piece - 09 [480p].mkv", 1),
        ],
    )
    res_op_s2e1 = StreamFileResolver(
        t_info_op_s01_pack,
        series=SeriesInfo(season=2, episode=1, alternate_episodes=[9]),
    ).resolve()
    assert res_op_s2e1 is not None
    assert "[HorribleSubs] One Piece - 09 [480p].mkv" in res_op_s2e1.name

    # 6. One Piece S5E1 (Cinemeta) -> feloldás S02-nek elnevezett pakkból (abszolút 62. rész)
    t_info_op_s02_pack = TorrentInfo(
        info_hash="hash_op_s2",
        name="One Piece S02 720p",
        size=5000,
        piece_size=1000,
        files=[
            make_file("One Piece S02 720p/[HorribleSubs] One Piece - 62 [720p].mkv", 0),
            make_file("One Piece S02 720p/[HorribleSubs] One Piece - 63 [720p].mkv", 1),
        ],
    )
    res_op_s5e1 = StreamFileResolver(
        t_info_op_s02_pack,
        series=SeriesInfo(season=5, episode=1, alternate_episodes=[62]),
    ).resolve()
    assert res_op_s5e1 is not None
    assert "[HorribleSubs] One Piece - 62 [720p].mkv" in res_op_s5e1.name

    # 7. Naruto Shippuden abszolút ep 500 -> S22E42 feloldása
    t_info_shippuden = TorrentInfo(
        info_hash="hash_ns",
        name="Naruto Shippuden",
        size=2000,
        piece_size=1000,
        files=[
            make_file("Naruto Shippuden - 499.mkv", 0),
            make_file("Naruto Shippuden - 500.mkv", 1),
        ],
    )
    res_ns = StreamFileResolver(
        t_info_shippuden,
        series=SeriesInfo(season=22, episode=42, alternate_episodes=[500]),
    ).resolve()
    assert res_ns is not None
    assert res_ns.name == "Naruto Shippuden - 500.mkv"


    # 8. Attack on Titan Season 3 Episode 2 - S01E02 és standalone "- 02" torrent kizárása, de S03E02 és "- 39" illesztése
    aot_s3_series = SeriesInfo(season=3, episode=2, alternate_episodes=[39])

    # S01E02 explicit 1. évad -> nem szabad illeszkednie!
    t_aot_s01 = TorrentInfo(
        info_hash="hash_aot_s01",
        name="Attack.on.Titan.S01E02.BDRIP.x264-Krissz.mkv",
        size=1000,
        piece_size=500,
        files=[make_file("Attack.on.Titan.S01E02.BDRIP.x264-Krissz.mkv", 0)],
    )
    assert StreamFileResolver(t_aot_s01, series=aot_s3_series).resolve() is None

    # Standalone "- 02" évad nélkül -> nem szabad S3E2-re illeszkednie!
    t_aot_standalone_02 = TorrentInfo(
        info_hash="hash_aot_02",
        name="Shingeki no Kyojin - 02 (BD 1280x720 x264 AAC).mkv",
        size=1000,
        piece_size=500,
        files=[make_file("Shingeki no Kyojin - 02 (BD 1280x720 x264 AAC).mkv", 0)],
    )
    assert StreamFileResolver(t_aot_standalone_02, series=aot_s3_series).resolve() is None

    # S03E02 -> egyeznie kell!
    t_aot_s03 = TorrentInfo(
        info_hash="hash_aot_s03",
        name="attack.on.titan.s03e02.dubbed.hdtv.x264-w4f.mkv",
        size=1000,
        piece_size=500,
        files=[make_file("attack.on.titan.s03e02.dubbed.hdtv.x264-w4f.mkv", 0)],
    )
    res_s03 = StreamFileResolver(t_aot_s03, series=aot_s3_series).resolve()
    assert res_s03 is not None
    assert "s03e02" in res_s03.name

    # Standalone "- 39" abszolút epizódszám -> egyeznie kell S3E2-re!
    t_aot_abs_39 = TorrentInfo(
        info_hash="hash_aot_39",
        name="[ReinForce] Shingeki no Kyojin - 39 (BDRip 1920x1080 x264 FLAC).mkv",
        size=1000,
        piece_size=500,
        files=[make_file("[ReinForce] Shingeki no Kyojin - 39 (BDRip 1920x1080 x264 FLAC).mkv", 0)],
    )
    res_abs_39 = StreamFileResolver(t_aot_abs_39, series=aot_s3_series).resolve()
    assert res_abs_39 is not None
    assert "- 39" in res_abs_39.name


    # 9. Code Geass R2 és Ordinal Season (pl. 2nd Season) felismerése és feloldása S2E2-re
    cg_s2_series = SeriesInfo(season=2, episode=2)

    # 720p BDRip S01-S02 pakk (ID 2137664)
    t_cg_720p_pack = TorrentInfo(
        info_hash="hash_cg_720p",
        name="Code Geass Lelouch of the Rebellion (BD_1280x720)",
        size=17000,
        piece_size=1000,
        files=[
            make_file("Code Geass Lelouch of the Rebellion (BD_1280x720)/Code Geass Hangyaku no Lelouch - 02 (BD 1280x720 x264 AAC).mkv", 0),
            make_file("Code Geass Lelouch of the Rebellion (BD_1280x720)/Code Geass Hangyaku no Lelouch R2 - 02 (BD 1280x720 x264 AAC).mkv", 1),
        ],
    )
    res_cg_720p = StreamFileResolver(t_cg_720p_pack, series=cg_s2_series).resolve()
    assert res_cg_720p is not None
    assert "R2 - 02" in res_cg_720p.name

    # 1080p BDRip S01-S02 pakk
    t_cg_1080p_pack = TorrentInfo(
        info_hash="hash_cg_1080p",
        name="Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)",
        size=54000,
        piece_size=2000,
        files=[
            make_file("Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)/[Yousei-raws] Code Geass - Hangyaku no Lelouch 02 [BDrip 1920x1080 x264 FLAC].mkv", 0),
            make_file("Code Geass - Hangyaku no Lelouch S01-S02 (BD_1920x1080)/[Yousei-raws] Code Geass - Hangyaku no Lelouch R2 02 [BDrip 1920x1080 x264 FLAC].mkv", 1),
        ],
    )
    res_cg_1080p = StreamFileResolver(t_cg_1080p_pack, series=cg_s2_series).resolve()
    assert res_cg_1080p is not None
    assert "R2 02" in res_cg_1080p.name

    # Ordinal season (2nd Season)
    t_mob_2nd = TorrentInfo(
        info_hash="hash_mob_2nd",
        name="Mob Psycho 100 2nd Season",
        size=5000,
        piece_size=1000,
        files=[
            make_file("Mob Psycho 100 2nd Season - 02.mkv", 0),
        ],
    )
    res_mob_2nd = StreamFileResolver(t_mob_2nd, series=SeriesInfo(season=2, episode=2)).resolve()
    assert res_mob_2nd is not None
    assert "2nd Season - 02" in res_mob_2nd.name


@pytest.mark.anyio
async def test_get_episode_mappings_generic_caching():
    resolver = TvdbResolver()
    # Mocking cache to verify generic caching mechanism
    resolver._cache["epmap_tt0388629_21_1"] = ([892], [])
    alts, seasons = await resolver.get_episode_mappings("tt0388629", 21, 1)
    assert alts == [892]
    assert seasons == []


@pytest.mark.anyio
async def test_resolve_kitsu_aot_season_isolation(monkeypatch):
    # Attack on Titan S3 Kitsu ID: 13569, Ep: 2
    resolver = TvdbResolver()
    async def mock_anime_kitsu(kitsu_id, episode):
        return "tt2560140", 3, 2, [39], [], "Attack on Titan Season 3"
    monkeypatch.setattr(resolver, "_resolve_from_anime_kitsu", mock_anime_kitsu)
    imdb_id, season, ep, alt_eps, alt_seasons = await resolver.resolve_kitsu_to_imdb("13569", 2)
    assert imdb_id == "tt2560140"
    assert season == 3
    assert ep == 2
    assert 39 in alt_eps
    # Kitsu belső season=1-et TILOS hozzáadni az alt_seasons-hoz, ha a valódi évad 3!
    assert 1 not in alt_seasons
    assert alt_seasons == []


@pytest.mark.anyio
async def test_get_alternate_imdb_ids_dbz():
    resolver = TvdbResolver()
    alts_1989 = await resolver.get_alternate_imdb_ids("tt0121220")
    assert "tt0214341" in alts_1989

    alts_1996 = await resolver.get_alternate_imdb_ids("tt0214341")
    assert "tt0121220" in alts_1996


@pytest.mark.anyio
async def test_get_episode_mappings_uses_alias_for_dbz():
    resolver = TvdbResolver()
    # Hermetic: Anime-Kitsu has no entry for tt0121220, so the cached alias tt0214341 must answer.
    requested: list[str] = []

    def kitsu_not_found(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(404)

    resolver._client = httpx.AsyncClient(transport=httpx.MockTransport(kitsu_not_found))
    # Ep 141 is Season 5 Episode 2
    resolver._series_epmap["tt0214341"] = {(5, 2): ([141], [])}
    try:
        alts, seasons = await resolver.get_episode_mappings("tt0121220", 5, 2)
    finally:
        await resolver.aclose()
    assert 141 in alts
    assert requested == ["https://anime-kitsu.strem.fun/meta/series/tt0121220.json"]


@pytest.mark.anyio
async def test_find_by_imdb_searches_alternate_imdb_ids():
    from tests.helpers import create_torrent_source

    mock_torrent_source_provider = AsyncMock()
    mock_settings_service = MagicMock()
    mock_settings_service.get_app_url.return_value = "http://localhost:7070"
    mock_preferences = MagicMock()
    mock_preferences.get_list.return_value = []
    mock_preferences.get_system_preferences.return_value = []

    source_1989 = create_torrent_source(
        indexer_id="ncore",
        indexer_name="nCore",
        torrent_id="t1",
        name="Dragon.Ball.Z.141.HUN.JAP.1080p.16mm.mkv",
        seeders=14,
        files=["Dragon.Ball.Z.141.HUN.JAP.1080p.16mm.mkv"],
    )
    source_1996 = create_torrent_source(
        indexer_id="ncore",
        indexer_name="nCore",
        torrent_id="t2",
        name="Dragon.Ball.Z.S01-S09.BDrip.HUN.x264-DenZo",
        seeders=304,
        files=["Dragon.Ball.Z.E141.BDrip.HUN.x264-DenZo.mkv"],
    )

    async def fake_find_by_imdb_id(iid):
        if iid == "tt0121220":
            return [source_1989], []
        elif iid == "tt0214341":
            return [source_1996], []
        return [], []

    mock_torrent_source_provider.find_by_imdb_id.side_effect = fake_find_by_imdb_id

    mock_torrents_service = MagicMock()
    mock_torrents_service.get_torrents.return_value = []

    service = TorrentStreamsService(
        db=AsyncMock(),
        torrent_source_provider_service=mock_torrent_source_provider,
        torrents_service=mock_torrents_service,
        settings_service=mock_settings_service,
        preferences_service=mock_preferences,
    )
    user = UserModel(id="u1", username="test", enable_smart_filter=False)
    series_info = SeriesInfo(season=5, episode=2, alternate_episodes=[141])

    streams, errors = await service.find_by_imdb(
        user=user,
        imdb_id="tt0121220",
        series=series_info,
        alternate_imdb_ids=["tt0214341"],
    )

    assert len(streams) == 2
    # The 304 seeder torrent should be sorted first
    assert streams[0].torrent_id == "t2"
    assert streams[0].seeders == 304
    assert streams[1].torrent_id == "t1"
    assert streams[1].seeders == 14


def test_parse_stream_id_tmdb():
    from app.modules.stremio.enums import StreamIdType
    from app.modules.stremio.schemas import TmdbStreamId
    from app.modules.stremio.utils import parse_stream_id

    # Movie
    res_movie = parse_stream_id("tmdb:273867")
    assert isinstance(res_movie, TmdbStreamId)
    assert res_movie.type == StreamIdType.TMDB
    assert res_movie.tmdb_id == "273867"
    assert res_movie.series_info is None

    # Series
    res_series = parse_stream_id("tmdb:273867:1:3")
    assert isinstance(res_series, TmdbStreamId)
    assert res_series.type == StreamIdType.TMDB
    assert res_series.tmdb_id == "273867"
    assert res_series.series_info is not None
    assert res_series.series_info.season == 1
    assert res_series.series_info.episode == 3


def test_indexer_definition_torrent_boolean_imdb_id():
    from app.modules.indexer_definitions.schemas.internal import (
        IndexerDefinitionTorrent,
    )

    t = IndexerDefinitionTorrent(
        torrent_id="12345",
        download_url="https://ncore.pro/torrents.php?action=download&id=12345",
        imdb_id=False,  # type: ignore
        seeders=10,
    )
    assert t.imdb_id is None

    t2 = IndexerDefinitionTorrent(
        torrent_id="12345",
        download_url="https://ncore.pro/torrents.php?action=download&id=12345",
        imdb_id="tt1234567",
        seeders=10,
    )
    assert t2.imdb_id == "tt1234567"


@pytest.mark.anyio
async def test_find_by_imdb_hungarian_show_title_queries():
    from unittest.mock import MagicMock

    from app.modules.preferences.service import PreferencesService
    from app.modules.torrent_source_provider.service import (
        TorrentSourceProviderService,
    )

    mock_provider = AsyncMock(spec=TorrentSourceProviderService)
    mock_provider.find_by_imdb_id.return_value = ([], [])

    queried_terms: list[str] = []

    async def fake_find_by_query(q):
        queried_terms.append(q)
        if q == "visszavago":
            mock_source = MagicMock()
            mock_source.indexer_torrent.indexer_account.indexer_id = "ncore"
            mock_source.indexer_torrent.torrent_id = "99"
            return [mock_source], []
        return [], []

    mock_provider.find_by_query.side_effect = fake_find_by_query

    mock_settings = AsyncMock(spec=SettingsService)
    mock_settings.get_app_url.return_value = "http://localhost:7070"

    mock_preferences = MagicMock(spec=PreferencesService)
    mock_preferences.get_list.return_value = []

    mock_torrents = MagicMock()
    mock_torrents.get_torrents.return_value = []

    service = TorrentStreamsService(
        db=AsyncMock(),
        torrent_source_provider_service=mock_provider,
        torrents_service=mock_torrents,
        settings_service=mock_settings,
        preferences_service=mock_preferences,
    )

    user = UserModel(id="user1", username="test", enable_smart_filter=False)
    await service.find_by_imdb(
        user=user,
        imdb_id="tt50140701",
        series=SeriesInfo(season=1, episode=1),
        fallback_title="A visszavágó - kapj el, ha tudsz!",
    )

    assert "visszavago S01" in queried_terms
    assert "A visszavago" in queried_terms
    assert "visszavago" in queried_terms


@pytest.mark.anyio
async def test_find_by_imdb_fallback_when_imdb_has_different_episode_only():
    from unittest.mock import MagicMock

    from app.common.torrent_info import TorrentFileInfo, TorrentInfo
    from app.modules.indexer_accounts.models import IndexerAccountModel
    from app.modules.indexer_accounts.schemas import IndexerAccountRef
    from app.modules.indexer_definitions.models import IndexerDefinitionModel
    from app.modules.preferences.service import PreferencesService
    from app.modules.torrent_source_provider.service import (
        TorrentSourceProviderService,
    )

    mock_provider = AsyncMock(spec=TorrentSourceProviderService)

    dummy_indexer_def = IndexerDefinitionModel(
        id="ncore", name="ncore", url="https://ncore.pro", details_path=""
    )
    dummy_indexer_account = IndexerAccountModel(
        indexer_id="ncore", username="test", password="pwd"
    )
    dummy_indexer_account.indexer_definition = dummy_indexer_def
    dummy_account_ref = IndexerAccountRef.from_model(dummy_indexer_account)

    t3_info = TorrentInfo(
        info_hash="hash3",
        name="A.visszavago.Kapj.el.ha.tudsz.S01E03.HUN.WEB-DL.1080p.mkv",
        size=1000000,
        piece_size=1000000,
        files=[
            TorrentFileInfo(
                index=0,
                name="A.visszavago.Kapj.el.ha.tudsz.S01E03.HUN.WEB-DL.1080p.mkv",
                path="A.visszavago.Kapj.el.ha.tudsz.S01E03.HUN.WEB-DL.1080p.mkv",
                size=1000000,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            )
        ],
    )
    mock_src_ep3 = MagicMock()
    mock_src_ep3.indexer_torrent.indexer_account = dummy_account_ref
    mock_src_ep3.indexer_torrent.torrent_id = "300"
    mock_src_ep3.indexer_torrent.imdb_id = "tt50140701"
    mock_src_ep3.indexer_torrent.seeders = 10
    mock_src_ep3.indexer_torrent.media_attributes = []
    mock_src_ep3.torrent_file.info = t3_info
    mock_src_ep3.torrent_file.torrent_id = "300"
    mock_src_ep3.torrent_file.info_hash = "hash3"

    mock_provider.find_by_imdb_id.return_value = ([mock_src_ep3], [])

    t1_info = TorrentInfo(
        info_hash="hash1",
        name="A.visszavago.Kapj.el.ha.tudsz.S01E01.HUN.WEB-DL.1080p.mkv",
        size=1000000,
        piece_size=1000000,
        files=[
            TorrentFileInfo(
                index=0,
                name="A.visszavago.Kapj.el.ha.tudsz.S01E01.HUN.WEB-DL.1080p.mkv",
                path="A.visszavago.Kapj.el.ha.tudsz.S01E01.HUN.WEB-DL.1080p.mkv",
                size=1000000,
                offset=0,
                start_piece_index=0,
                end_piece_index=0,
                is_video=True,
            )
        ],
    )
    mock_src_ep1 = MagicMock()
    mock_src_ep1.indexer_torrent.indexer_account = dummy_account_ref
    mock_src_ep1.indexer_torrent.torrent_id = "100"
    mock_src_ep1.indexer_torrent.imdb_id = None
    mock_src_ep1.indexer_torrent.seeders = 20
    mock_src_ep1.indexer_torrent.media_attributes = []
    mock_src_ep1.torrent_file.info = t1_info
    mock_src_ep1.torrent_file.torrent_id = "100"
    mock_src_ep1.torrent_file.info_hash = "hash1"

    searched_queries = []

    async def fake_query(q):
        searched_queries.append(q)
        return [mock_src_ep1], []

    mock_provider.find_by_query.side_effect = fake_query

    mock_settings = AsyncMock(spec=SettingsService)
    mock_settings.get_app_url.return_value = "http://localhost:7070"

    mock_preferences = MagicMock(spec=PreferencesService)
    mock_preferences.get_list.return_value = []

    mock_torrents = MagicMock()
    mock_torrents.get_torrents.return_value = []

    service = TorrentStreamsService(
        db=AsyncMock(),
        torrent_source_provider_service=mock_provider,
        torrents_service=mock_torrents,
        settings_service=mock_settings,
        preferences_service=mock_preferences,
    )

    user = UserModel(id="user1", username="test", enable_smart_filter=False)
    streams, errors = await service.find_by_imdb(
        user=user,
        imdb_id="tt50140701",
        series=SeriesInfo(season=1, episode=1),
        fallback_title=None,
    )

    mock_provider.find_by_imdb_id.assert_awaited_once_with("tt50140701")
    assert "visszavago Kapj el ha tudsz S01" in searched_queries
    assert len(streams) == 1
    assert streams[0].torrent_id == "100"
    assert "S01E01" in streams[0].file_name


@pytest.mark.anyio
async def test_batch_torrent_download_and_save_single_transaction():
    from app.modules.indexers.schemas.internal import DownloadedTorrentFile
    from app.modules.torrent_source_provider.service import TorrentSourceProviderService

    mock_indexers = AsyncMock()
    mock_isolated_files = MagicMock()
    mock_isolated_files.find_snapshots.return_value = []

    async def fake_download(indexer_id: str, torrent_id: str, url: str):
        return DownloadedTorrentFile(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            torrent_bytes=f"bytes-{torrent_id}".encode(),
        )

    mock_indexers.download_torrent.side_effect = fake_download

    from tests.helpers import create_torrent_source

    sources_by_id = {
        tid: create_torrent_source(
            indexer_id="ncore",
            indexer_name="nCore",
            torrent_id=tid,
            name=f"Torrent.{tid}",
        )
        for tid in ["101", "102", "103"]
    }
    mock_isolated_files.create_many.return_value = [
        s.torrent_file for s in sources_by_id.values()
    ]

    provider = TorrentSourceProviderService(
        indexers_service=mock_indexers,
        isolated_torrent_files_service=mock_isolated_files,
    )

    torrents = [s.indexer_torrent for s in sources_by_id.values()]

    sources = await provider._shared_search()._sync_torrent_files(torrents)
    assert len(sources) == 3
    # Egyetlen kötegelt create_many tranzakció futott le 3 külön create helyett
    mock_isolated_files.create_many.assert_called_once()
    batch_arg = mock_isolated_files.create_many.call_args.args[0]
    assert len(batch_arg) == 3
    assert [item[1] for item in batch_arg] == ["101", "102", "103"]


def test_relay_tighter_piece_deadlines(monkeypatch):
    # The fork's legacy start/readahead contract (selectable for rollback since gsp02-v4 made the
    # upstream-like policy the default).
    from app.common.torrent_info import TorrentFileInfo
    from app.config import config

    monkeypatch.setattr(config, "relay_start_policy", "legacy")
    monkeypatch.setattr(config, "relay_readahead_policy", "legacy")
    from app.modules.relay.entities import File, Stream, Torrent

    mock_handle = MagicMock()
    mock_handle.have_piece.return_value = False
    mock_handle.piece_priorities.return_value = [0] * 20

    torrent = object.__new__(Torrent)
    torrent.info_hash = "deadbeef"
    torrent.piece_size = 1000
    torrent.prefetch_piece_count = 5
    torrent.critical_piece_count = 2
    torrent.torrent_handle = mock_handle
    torrent.files = {}

    file_info = TorrentFileInfo(
        index=0,
        path="video.mkv",
        name="video.mkv",
        size=15000,
        offset=0,
        start_piece_index=0,
        end_piece_index=14,
        is_video=True,
    )
    f = File(file_info=file_info, torrent=torrent)
    torrent.files[0] = f

    stream = Stream(
        stream_id="s1",
        playback_id="p1",
        user_id="u1",
        torrent=torrent,
        file=f,
        stream_start_byte=2000,
        stream_end_byte=12000,
    )
    assert stream.current_stream_piece == 2

    deadlines = torrent.get_deadlines()
    # Fájlhatárok (0 és 14) -> 0 ms, aktuális piece (2) -> 0 ms
    assert deadlines[2] == 0
    # Következő piece (3, distance=1) -> 300 ms
    assert deadlines[3] == 300
    # További előtöltött piece-ek: 1000 + distance * 500 ms
    assert deadlines[4] == 2000  # distance=2 -> 1000 + 2*500
    assert deadlines[5] == 2500  # distance=3 -> 1000 + 3*500


@pytest.mark.anyio
async def test_get_alternate_imdb_ids_fast_path():
    resolver = TvdbResolver()
    # Filmeknél (is_series=False) külső hívás nélkül, azonnal üres listát ad vissza
    alts = await resolver.get_alternate_imdb_ids("tt1375666", is_series=False, allow_dynamic_search=True)
    assert alts == []

    # allow_dynamic_search=False esetén még sorozatoknál is azonnal visszatér, ha nem ismert anime
    alts_series = await resolver.get_alternate_imdb_ids("tt4574334", is_series=True, allow_dynamic_search=False)
    assert alts_series == []

    # Ismert animénél (DBZ) viszont allow_dynamic_search=False esetén is azonnal megadja a statikus párt
    alts_anime = await resolver.get_alternate_imdb_ids("tt0121220", is_series=True, allow_dynamic_search=False)
    assert "tt0214341" in alts_anime


@pytest.mark.anyio
async def test_get_alternate_imdb_ids_false_positive_rejection():
    resolver = TvdbResolver()
    # Mockoljuk a get_title_by_imdb-t
    resolver.get_title_by_imdb = AsyncMock(return_value="Inception")  # type: ignore[method-assign]

    # Mockoljuk a kitsu választ, mintha visszadná a Cobol Job rövidfilmet
    mock_client = AsyncMock()
    mock_kitsu_resp = MagicMock()
    mock_kitsu_resp.status_code = 200
    mock_kitsu_resp.json.return_value = {
        "data": [
            {
                "id": "5951",
                "attributes": {
                    "canonicalTitle": "Inception: The Cobol Job",
                    "titles": {"en": "Inception: The Cobol Job"},
                },
            }
        ]
    }
    mock_client.get.return_value = mock_kitsu_resp
    resolver._get_client = lambda: mock_client  # type: ignore[assignment]

    # Mivel "Inception" != "Inception: The Cobol Job", a szigorú címegyezésnek vissza kell utasítania
    alts = await resolver.get_alternate_imdb_ids("tt1375666", is_series=True, allow_dynamic_search=True)
    assert alts == []








