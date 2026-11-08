from unittest.mock import MagicMock

import pytest

from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef, IndexerDefinitionRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.stream.utils.subtitles import ass_to_vtt
from app.modules.stremio.enums import ShortManifestResource
from app.modules.stremio.schemas import StremioStream, StremioSubtitle
from app.modules.stremio.service import StremioService
from app.modules.torrent_streams.schemas import TorrentStream, TorrentStreamSubtitle
from app.modules.torrent_streams.utils.resolver_helpers import (
    detect_subtitle_language,
    is_extra_file,
    is_extra_folder,
)
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver
from app.modules.users.models import UserModel


def make_file(
    path: str, index: int, size: int = 1000, is_video: bool = True
) -> TorrentFileInfo:
    name = path.split("/")[-1]
    ext = "." + name.split(".")[-1].lower() if "." in name else ""
    is_sub = ext in {".srt", ".ass", ".ssa", ".vtt", ".sub"}
    return TorrentFileInfo(
        name=name,
        path=path,
        size=size,
        offset=index * 1000,
        start_piece_index=index,
        end_piece_index=index,
        is_video=is_video,
        is_subtitle=is_sub,
        index=index,
    )


def test_extra_folder_and_file_helpers():
    assert is_extra_folder("Extras") is True
    assert is_extra_folder("extras") is True
    assert is_extra_folder("[Extras]") is True
    assert is_extra_folder("00. Extrák") is True
    assert is_extra_folder("Season 2 Extras") is True
    assert is_extra_folder("Season 1") is False

    assert is_extra_file("Noragami Aragoto - Extra 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - SP 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - 01.mkv") is False


def test_detect_subtitle_language():
    assert detect_subtitle_language("Noragami.hun.ass")[0] == "hun"
    assert detect_subtitle_language("Noragami.hu.srt")[0] == "hun"
    assert detect_subtitle_language("Noragami [HunSub].ass")[0] == "hun"
    assert detect_subtitle_language("Noragami.eng.srt")[0] == "eng"
    assert detect_subtitle_language("Noragami.ger.srt")[0] == "ger"
    assert detect_subtitle_language("Noragami.hun.forced.srt") == (
        "hun",
        "Hungarian (Forced)",
    )
    assert detect_subtitle_language("01.ass") == ("hun", "Hungarian (Torrent)")
    assert detect_subtitle_language("Noragami.fre.srt")[0] == "fre"
    assert detect_subtitle_language("Noragami.spa.srt")[0] == "spa"
    assert detect_subtitle_language("Noragami.ita.srt")[0] == "ita"
    assert detect_subtitle_language("Noragami.rus.srt")[0] == "rus"
    # Ismeretlen / nyelvjelölés nélküli feliratok alapértelmezetten magyarként kezelendők
    assert detect_subtitle_language("subtitles.srt")[0] == "hun"
    assert detect_subtitle_language("ep01.ass")[0] == "hun"
    assert detect_subtitle_language("Noragami - 01.ass")[0] == "hun"
    assert detect_subtitle_language("Kaland es Mas - 01.srt")[0] == "hun"
    assert detect_subtitle_language("Film de jo - 01.srt")[0] == "hun"
    assert detect_subtitle_language("ep01.en.srt")[0] == "eng"
    assert detect_subtitle_language("ep01.de.srt")[0] == "ger"
    # Mappanévi felülbírálási tesztek (a fájlnév explicit nyelve prioritást élvez a release mappával szemben)
    assert detect_subtitle_language("English.srt", "Movie.HUN.1080p/Subs")[0] == "eng"
    assert detect_subtitle_language("German.srt", "Movie.HUN.1080p/Subs")[0] == "ger"
    assert detect_subtitle_language("01.srt", "Movie.HUN.1080p/Subs/English")[0] == "eng"
    assert detect_subtitle_language("01.srt", "Movie.HUN.1080p/Subs/hun")[0] == "hun"
    assert detect_subtitle_language("01.ass", "Noragami [HunSub]")[0] == "hun"


def test_resolve_subtitles_ignores_other_episodes_in_packs():
    # Két rész egy pakkban és mindkettőhöz felirat
    v1 = make_file("Attack on Titan/Attack on Titan - HunSub - 01 [1080p].mkv", 0)
    v2 = make_file("Attack on Titan/Attack on Titan - HunSub - 02 [1080p].mkv", 1)
    s1 = make_file("Attack on Titan/Attack on Titan - 01.ass", 2, is_video=False)
    s2 = make_file("Attack on Titan/Attack on Titan - 02.ass", 3, is_video=False)

    t_info = TorrentInfo(
        info_hash="hash_aot",
        name="Attack on Titan [1080p]",
        size=4000,
        piece_size=1000,
        files=[v1, v2, s1, s2],
    )

    resolver_ep1 = StreamFileResolver(t_info, series=SeriesInfo(season=1, episode=1))
    resolved_subs_ep1 = resolver_ep1.resolve_subtitles(v1)
    assert len(resolved_subs_ep1) == 1
    assert resolved_subs_ep1[0].name == "Attack on Titan - 01.ass"

    resolver_ep2 = StreamFileResolver(t_info, series=SeriesInfo(season=1, episode=2))
    resolved_subs_ep2 = resolver_ep2.resolve_subtitles(v2)
    assert len(resolved_subs_ep2) == 1
    assert resolved_subs_ep2[0].name == "Attack on Titan - 02.ass"


@pytest.mark.anyio
async def test_get_subtitles_played_stream_matching_and_fallback():
    mock_settings = MagicMock()
    mock_settings.get_app_url.return_value = "http://test-app.com"
    mock_torrent_streams = MagicMock()

    service = StremioService(
        torrent_streams_service=mock_torrent_streams,
        settings_service=mock_settings,
    )
    user = UserModel(id="test-user", username="test")

    sub_t1 = StremioSubtitle(
        id="t1-sub",
        url="http://test-app.com/sub/t1.vtt",
        lang="hun",
        label="Hungarian",
    )

    from app.modules.stremio.schemas import BehaviorHints, ImdbStreamId
    # Stream 1 felirattal
    stream1 = StremioStream(
        name="1080p",
        description="📁 video1.mkv",
        url="http://test-app.com/video1.mkv",
        subtitles=[sub_t1],
        behavior_hints=BehaviorHints(filename="video1.mkv", video_size=500000),
    )
    # Stream 2 saját felirat nélkül
    stream2 = StremioStream(
        name="720p",
        description="📁 video2.mkv",
        url="http://test-app.com/video2.mkv",
        subtitles=None,
        behavior_hints=BehaviorHints(filename="video2.mkv", video_size=300000),
    )

    # MagicMock for async get_streams
    async def mock_get_streams(*args, **kwargs):
        return [stream1, stream2]

    service.get_streams = mock_get_streams

    parsed_id = ImdbStreamId(
        imdb_id="tt123456", series_info=SeriesInfo(season=1, episode=1)
    )

    # 1. Ha a video1-et játsszuk le: a saját feliratát adja vissza
    subs1 = await service.get_subtitles(
        user=user,
        parsed_id=parsed_id,
        extra="filename=video1.mkv&videoSize=500000",
    )
    assert len(subs1) == 1
    assert subs1[0].id == "t1-sub"

    # 2. Alapértelmezetten (enable_fallback_subtitles=False) ha a video2-t játsszuk le, NEM kölcsönöz feliratot:
    subs2_disabled = await service.get_subtitles(
        user=user,
        parsed_id=parsed_id,
        extra="filename=video2.mkv&videoSize=300000",
    )
    assert subs2_disabled == []

    # 3. Ha be van kapcsolva az enable_fallback_subtitles=True: fallback a video1 feliratára
    user.enable_fallback_subtitles = True
    subs2_enabled = await service.get_subtitles(
        user=user,
        parsed_id=parsed_id,
        extra="filename=video2.mkv&videoSize=300000",
    )
    assert len(subs2_enabled) == 1
    assert subs2_enabled[0].id == "t1-sub"



def test_resolve_subtitles_for_series():
    v1 = make_file("Noragami Aragoto/Noragami Aragoto - 01 [1080p].mkv", 0)
    v2 = make_file("Noragami Aragoto/Noragami Aragoto - 02 [1080p].mkv", 1)
    s1 = make_file(
        "Noragami Aragoto/Noragami Aragoto - 01 [1080p].ass", 2, is_video=False
    )
    s2 = make_file(
        "Noragami Aragoto/Noragami Aragoto - 02 [1080p].ass", 3, is_video=False
    )
    extra_sub = make_file("Noragami Aragoto/Extras/01.ass", 4, is_video=False)

    t_info = TorrentInfo(
        info_hash="hash_sub_pack",
        name="Noragami Aragoto [1080p]",
        size=4000,
        piece_size=1000,
        files=[v1, v2, s1, s2, extra_sub],
    )

    resolver = StreamFileResolver(t_info, series=SeriesInfo(season=2, episode=1))
    resolved_subs = resolver.resolve_subtitles(v1)

    assert len(resolved_subs) == 1
    assert resolved_subs[0].name == "Noragami Aragoto - 01 [1080p].ass"
    assert extra_sub not in resolved_subs


def test_stremio_stream_includes_subtitles():
    dummy_indexer_def = IndexerDefinitionModel(
        id="ncore", name="ncore", url="https://ncore.pro", details_path=""
    )
    dummy_indexer_account = IndexerAccountModel(
        indexer_id="ncore", username="test", password="pwd"
    )
    dummy_indexer_account.indexer_definition = dummy_indexer_def

    sub = TorrentStreamSubtitle(
        id="sub1",
        file_name="01.ass",
        file_index=1,
        file_size=50000,
        url="http://localhost:7070/api/key/subtitles/token/01.ass",
        lang="hun",
        label="Hungarian (Torrent)",
    )

    t_stream = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(dummy_indexer_account),
        torrent_id="1",
        info_hash="hash",
        torrent_name="Noragami Aragoto",
        file_name="Noragami Aragoto - 01.mkv",
        file_size=1000000,
        file_index=0,
        play_url="http://localhost:7070/api/key/stream/token",
        attributes=[IndexerDefinitionRef.from_model(dummy_indexer_def)],
        subtitles=[sub],
        is_persisted_torrent=False,
    )

    stremio_stream = StremioStream.from_imdb_torrent_stream(t_stream, is_series=True)
    assert stremio_stream.subtitles is not None
    assert len(stremio_stream.subtitles) == 1
    assert stremio_stream.subtitles[0].id == "sub1"
    assert (
        stremio_stream.subtitles[0].url
        == "http://localhost:7070/api/key/subtitles/token/01.ass"
    )
    assert stremio_stream.subtitles[0].lang == "hun"
    assert stremio_stream.subtitles[0].label == "Hungarian (Torrent)"


def test_ass_to_vtt_conversion():
    ass_sample = """[Script Info]
Title: Noragami Aragoto 03
ScriptType: v4.00+

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:23.45,0:01:27.89,Default,,0,0,0,,{\\pos(192,200)}Szia,\\hez egy teszt felirat!\\NMásodik sor.
Dialogue: 0,0:02:10.00,0:02:15.50,Default,,0,0,0,,{\\c&H0000FF&}{\\b1}Vastag és színes{\\b0}
Dialogue: 0,0:02:20.00,0:02:25.00,Default,,0,0,0,,{\\p1}m 0 0 l 100 0 100 100 0 100{\\p0}
Dialogue: 0,0:03:00.10.20,0:03:05.10,Default,,0,0,0,,Többpontos időbélyeg teszt
"""
    vtt = ass_to_vtt(ass_sample)
    assert vtt.startswith("WEBVTT\n")
    assert "00:01:23.450 --> 00:01:27.890" in vtt
    assert "Szia, ez egy teszt felirat!\nMásodik sor." in vtt
    assert "\\h" not in vtt
    assert "00:02:10.000 --> 00:02:15.500" in vtt
    assert "Vastag és színes" in vtt
    assert "{\\pos" not in vtt
    assert "{\\c&H" not in vtt
    assert "m 0 0 l 100" not in vtt
    assert "Többpontos időbélyeg teszt" in vtt


def test_manifest_includes_subtitles_resource():
    mock_settings = MagicMock()
    mock_settings.get_app_url.return_value = "http://test-app.com"
    mock_torrent_streams = MagicMock()

    service = StremioService(
        torrent_streams_service=mock_torrent_streams,
        settings_service=mock_settings,
    )
    manifest = service.manifest()

    assert ShortManifestResource.SUBTITLES in manifest.resources
    assert "subtitles" in [getattr(r, "value", r) for r in manifest.resources]


@pytest.mark.anyio
async def test_get_streams_and_subtitles_caching_deduplication():
    import asyncio
    from unittest.mock import AsyncMock

    from app.modules.stremio.schemas import ImdbStreamId
    from app.modules.stremio.tvdb_resolver import TvdbResolver

    mock_settings = MagicMock()
    mock_settings.get_app_url.return_value = "http://test-app.com"

    dummy_indexer_def = IndexerDefinitionModel(
        id="ncore", name="ncore", url="https://ncore.pro", details_path=""
    )
    dummy_indexer_account = IndexerAccountModel(
        indexer_id="ncore", username="test", password="pwd"
    )
    dummy_indexer_account.indexer_definition = dummy_indexer_def

    sub = TorrentStreamSubtitle(
        id="sub1",
        file_name="01.vtt",
        file_index=1,
        file_size=50000,
        url="http://test-app.com/api/key/subtitles/token/01.vtt",
        lang="hun",
        label="Hungarian",
    )
    t_stream = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(dummy_indexer_account),
        torrent_id="1",
        info_hash="hash_cache_test",
        torrent_name="Test Movie",
        file_name="Test.Movie.1080p.mkv",
        file_size=1000000,
        file_index=0,
        play_url="http://test-app.com/api/key/stream/token",
        attributes=[IndexerDefinitionRef.from_model(dummy_indexer_def)],
        subtitles=[sub],
        is_persisted_torrent=False,
    )

    mock_torrent_streams = AsyncMock()
    mock_torrent_streams.find_by_imdb.return_value = ([t_stream], [])

    mock_tvdb_resolver = AsyncMock(spec=TvdbResolver)
    mock_tvdb_resolver.get_alternate_imdb_ids.return_value = []

    service = StremioService(
        torrent_streams_service=mock_torrent_streams,
        settings_service=mock_settings,
        tvdb_resolver_service=mock_tvdb_resolver,
    )
    user = UserModel(id="cache-test-user", username="test")
    parsed_id = ImdbStreamId(imdb_id="tt8888888", series_info=None)

    # Párhuzamos /stream és /subtitles kérés + utólagos /subtitles lejátszási kérés
    streams_res, subs_res = await asyncio.gather(
        service.get_streams(user, parsed_id),
        service.get_subtitles(user, parsed_id),
    )
    subs_after_play = await service.get_subtitles(
        user, parsed_id, extra="videoSize=1000000"
    )

    assert len(streams_res) == 1
    assert len(subs_res) == 1
    assert len(subs_after_play) == 1
    # Az nCore / find_by_imdb keresés mindössze 1-szer futhatott le a 3 kérés ellenére!
    assert mock_torrent_streams.find_by_imdb.await_count == 1


@pytest.mark.anyio
async def test_active_playback_selects_only_played_torrent_subtitle():
    from unittest.mock import AsyncMock

    from app.modules.stream.active_playback import (
        clear_active_playbacks,
        record_active_playback,
    )
    from app.modules.stremio.schemas import ImdbStreamId
    from app.modules.stremio.tvdb_resolver import TvdbResolver

    clear_active_playbacks()

    mock_settings = MagicMock()
    mock_settings.get_app_url.return_value = "http://test-app.com"

    dummy_indexer_def = IndexerDefinitionModel(
        id="ncore", name="ncore", url="https://ncore.pro", details_path=""
    )
    dummy_indexer_account = IndexerAccountModel(
        indexer_id="ncore", username="test", password="pwd"
    )
    dummy_indexer_account.indexer_definition = dummy_indexer_def

    sub1 = TorrentStreamSubtitle(
        id="2114813-948",
        file_name="Naruto - 004.srt",
        file_index=948,
        file_size=20000,
        url="http://test-app.com/api/key/subtitles/tok1/Naruto%20-%20004.srt",
        lang="hun",
        label="Hungarian (Torrent)",
    )
    sub2 = TorrentStreamSubtitle(
        id="3246976-3",
        file_name="Naruto - E004.srt",
        file_index=3,
        file_size=22000,
        url="http://test-app.com/api/key/subtitles/tok2/Naruto%20-%20E004.srt",
        lang="hun",
        label="Hungarian",
    )

    s1 = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(dummy_indexer_account),
        torrent_id="2114813",
        info_hash="hash_naruto_1",
        torrent_name="Naruto Pack 1",
        file_name="Naruto - 004.mkv",
        file_size=115115777,
        file_index=447,
        play_url="http://test-app.com/api/key/stream/tok1",
        attributes=[IndexerDefinitionRef.from_model(dummy_indexer_def)],
        subtitles=[sub1],
        is_persisted_torrent=False,
    )
    s2 = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(dummy_indexer_account),
        torrent_id="3246976",
        info_hash="hash_naruto_2",
        torrent_name="Naruto Pack 2",
        file_name="Naruto - E004.mkv",
        file_size=262617522,
        file_index=2,
        play_url="http://test-app.com/api/key/stream/tok2",
        attributes=[IndexerDefinitionRef.from_model(dummy_indexer_def)],
        subtitles=[sub2],
        is_persisted_torrent=False,
    )

    mock_torrent_streams = AsyncMock()
    mock_torrent_streams.find_by_imdb.return_value = ([s1, s2], [])
    mock_tvdb_resolver = AsyncMock(spec=TvdbResolver)
    mock_tvdb_resolver.get_alternate_imdb_ids.return_value = []

    service = StremioService(
        torrent_streams_service=mock_torrent_streams,
        settings_service=mock_settings,
        tvdb_resolver_service=mock_tvdb_resolver,
    )
    user = UserModel(id="naruto-user", username="test", api_key="test-api-key")
    parsed_id = ImdbStreamId(imdb_id="tt0988824", series_info=None)

    # Ha a 2. torrentet (3246976) indította el a lejátszó, és a Nuvio paraméterek nélkül hívja a /subtitles végpontot:
    record_active_playback(
        user_id=user.id, indexer_id="ncore", torrent_id="3246976"
    )
    subs = await service.get_subtitles(user, parsed_id)
    assert len(subs) == 1
    assert subs[0].id == "3246976-3"
    clear_active_playbacks()


@pytest.mark.anyio
async def test_fallback_subtitles_respects_toggle_and_download_full_torrent():
    from unittest.mock import AsyncMock

    from app.modules.stremio.schemas import ImdbStreamId
    from app.modules.stremio.tvdb_resolver import TvdbResolver

    mock_settings = MagicMock()
    mock_settings.get_app_url.return_value = "http://test-app.com"

    ncore_def = IndexerDefinitionModel(
        id="ncore",
        name="nCore",
        url="https://ncore.pro",
        details_path="",
        requires_full_download=False,
    )
    ncore_acc = IndexerAccountModel(
        indexer_id="ncore",
        username="test",
        password="pwd",
        download_full_torrent=False,
    )
    ncore_acc.indexer_definition = ncore_def

    sub1 = TorrentStreamSubtitle(
        id="812207-102",
        file_name="FMA - 01.vtt",
        file_index=102,
        file_size=30000,
        url="http://test-app.com/api/key/subtitles/tok1/FMA%20-%2001.vtt",
        lang="hun",
        label="Hungarian (Torrent)",
    )

    s_without_sub = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(ncore_acc),
        torrent_id="2355325",
        info_hash="hash_fma_1",
        torrent_name="FMA PluSUltra",
        file_name="FMA.S01E01.mkv",
        file_size=500000000,
        file_index=0,
        play_url="http://test-app.com/api/key/stream/tok_nosub",
        attributes=[IndexerDefinitionRef.from_model(ncore_def)],
        subtitles=None,
        is_persisted_torrent=False,
    )
    s_with_sub = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(ncore_acc),
        torrent_id="812207",
        info_hash="hash_fma_2",
        torrent_name="FMA BD",
        file_name="FMA - 01.mkv",
        file_size=700000000,
        file_index=0,
        play_url="http://test-app.com/api/key/stream/tok_sub",
        attributes=[IndexerDefinitionRef.from_model(ncore_def)],
        subtitles=[sub1],
        is_persisted_torrent=False,
    )

    mock_torrent_streams = AsyncMock()
    mock_torrent_streams.find_by_imdb.return_value = ([s_without_sub, s_with_sub], [])
    mock_tvdb_resolver = AsyncMock(spec=TvdbResolver)
    mock_tvdb_resolver.get_alternate_imdb_ids.return_value = []

    service = StremioService(
        torrent_streams_service=mock_torrent_streams,
        settings_service=mock_settings,
        tvdb_resolver_service=mock_tvdb_resolver,
    )
    parsed_id = ImdbStreamId(imdb_id="tt1355642", series_info=None)

    # 1. Kikapcsolt opció mellett (alapértelmezett) s_without_sub NEM kap feliratot
    user_off = UserModel(
        id="fma-user-off",
        username="test1",
        api_key="key1",
        enable_fallback_subtitles=False,
    )
    streams_off = await service.get_streams(user_off, parsed_id)
    assert streams_off[0].subtitles is None
    assert streams_off[1].subtitles is not None

    # 2. Bekapcsolt opció + download_full_torrent=False mellett s_without_sub kölcsönöz feliratot
    user_on = UserModel(
        id="fma-user-on",
        username="test2",
        api_key="key2",
        enable_fallback_subtitles=True,
    )
    streams_on = await service.get_streams(user_on, parsed_id)
    assert streams_on[0].subtitles is not None
    assert streams_on[0].subtitles[0].id == "812207-102"

    # 3. Ha az indexeren be van kapcsolva a teljes torrent letöltése (download_full_torrent=True),
    # még bekapcsolt opció mellett SEM kölcsönöz feliratot!
    full_download_acc = IndexerAccountRef.from_model(ncore_acc).model_copy(
        update={"download_full_torrent": True}
    )
    s_without_sub.indexer_account = full_download_acc
    s_with_sub.indexer_account = full_download_acc
    user_full = UserModel(
        id="fma-user-full",
        username="test3",
        api_key="key3",
        enable_fallback_subtitles=True,
    )
    streams_full = await service.get_streams(user_full, parsed_id)
    assert streams_full[0].subtitles is None


def test_matched_subtitle_piece_prefetching_on_video_start():
    from app.modules.relay.entities import Stream, Torrent

    # Epizód 1 (piece 0), Epizód 2 (piece 5), Felirat 1 (piece 10), Felirat 2 (piece 15)
    v1 = TorrentFileInfo(
        name="Naruto - 01.mkv",
        path="Naruto/Naruto - 01.mkv",
        size=1000,
        offset=0,
        start_piece_index=0,
        end_piece_index=0,
        is_video=True,
        is_subtitle=False,
        index=0,
    )
    v2 = TorrentFileInfo(
        name="Naruto - 02.mkv",
        path="Naruto/Naruto - 02.mkv",
        size=1000,
        offset=5000,
        start_piece_index=5,
        end_piece_index=5,
        is_video=True,
        is_subtitle=False,
        index=1,
    )
    s1 = TorrentFileInfo(
        name="Naruto - 01.srt",
        path="Naruto/Naruto - 01.srt",
        size=500,
        offset=10000,
        start_piece_index=10,
        end_piece_index=10,
        is_video=False,
        is_subtitle=True,
        index=2,
    )
    s2 = TorrentFileInfo(
        name="Naruto - 02.srt",
        path="Naruto/Naruto - 02.srt",
        size=500,
        offset=15000,
        start_piece_index=15,
        end_piece_index=15,
        is_video=False,
        is_subtitle=True,
        index=3,
    )

    t_info = TorrentInfo(
        info_hash="hash_prefetch",
        name="Naruto Pack",
        size=20000,
        piece_size=1000,
        files=[v1, v2, s1, s2],
    )

    mock_handle = MagicMock()
    mock_handle.have_piece.return_value = False
    mock_service = MagicMock()
    mock_service._torrent_connections_limit = 20

    torrent = Torrent(
        torrent_handle=mock_handle,
        torrent_info=t_info,
        service=mock_service,
        default_priority=0,
    )

    # Elindítjuk a 2. epizód (index=1, piece=5) lejátszását:
    file_ep2 = torrent.files[1]
    Stream(
        stream_id="s-ep2",
        playback_id="p-ep2",
        user_id="u1",
        torrent=torrent,
        file=file_ep2,
        stream_start_byte=0,
        stream_end_byte=999,
    )

    deadlines = torrent.get_deadlines()
    # A 2. epizód videójának első piece-e (5) 0 ms deadline-t kap:
    assert deadlines.get(5) == 0
    # A 2. epizódhoz tartozó felirat piece-e (15) 500 ms előtöltési deadline-t kap:
    assert deadlines.get(15) == 500
    # Az 1. epizód feliratának piece-e (10) NEM kap felesleges előtöltést:
    assert 10 not in deadlines


def test_subtitle_memory_cache_and_range_support():
    from app.modules.stream.router import (
        _build_cached_subtitle_response,
        _get_cached_subtitle,
        _put_cached_subtitle,
        _subtitle_content_cache,
    )
    from app.modules.stream.service import StreamService

    _subtitle_content_cache.clear()
    key = ("ncore", "812207", 102, True)
    sample_vtt = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nTeszt felirat\n"

    _put_cached_subtitle(key, "text/vtt; charset=utf-8", "01.vtt", sample_vtt)
    cached = _get_cached_subtitle(key)
    assert cached is not None
    media_type, disp_name, content_bytes = cached
    assert disp_name == "01.vtt"
    assert content_bytes == sample_vtt

    dummy_stream_service = StreamService(
        torrents_service=MagicMock(),
        torrent_files_service=MagicMock(),
        indexers_service=MagicMock(),
        relay_service=MagicMock(),
        isolated_torrent_files_service=MagicMock(),
    )

    # 1. Teljes GET kérés (200 OK)
    resp_full = _build_cached_subtitle_response(
        request_method="GET",
        media_type=media_type,
        disp_name=disp_name,
        content_bytes=content_bytes,
        range_header=None,
        convert_to_vtt=True,
        stream_service=dummy_stream_service,
    )
    assert resp_full.status_code == 200
    assert resp_full.body == sample_vtt

    # 2. Range GET kérés nyers .srt feliratra (206 Partial Content)
    resp_range = _build_cached_subtitle_response(
        request_method="GET",
        media_type="text/plain; charset=utf-8",
        disp_name="01.srt",
        content_bytes=sample_vtt,
        range_header="bytes=0-5",
        convert_to_vtt=False,
        stream_service=dummy_stream_service,
    )
    assert resp_range.status_code == 206
    assert resp_range.body == b"WEBVTT"
    _subtitle_content_cache.clear()


def test_resolve_subtitles_prefix_boundary_matching():
    # Filmgyűjtemény (nem sorozat): Movie 1.mkv nem illeszkedhet a Movie 10.hun.srt-re!
    v1 = make_file("Collection/Movie 1.mkv", 0)
    v2 = make_file("Collection/Movie 10.mkv", 1)
    s_movie1 = make_file("Collection/Movie 1.hun.srt", 2, is_video=False)
    s_movie10 = make_file("Collection/Movie 10.hun.srt", 3, is_video=False)

    t_info = TorrentInfo(
        info_hash="hash_movies",
        name="Movie Collection",
        size=4000,
        piece_size=1000,
        files=[v1, v2, s_movie1, s_movie10],
    )

    resolver = StreamFileResolver(t_info, series=None)
    resolved_v1 = resolver.resolve_subtitles(v1)
    resolved_v2 = resolver.resolve_subtitles(v2)

    assert len(resolved_v1) == 1
    assert resolved_v1[0].name == "Movie 1.hun.srt"

    assert len(resolved_v2) == 1
    assert resolved_v2[0].name == "Movie 10.hun.srt"


@pytest.mark.anyio
async def test_concurrent_wait_for_active_binge_group():
    import asyncio

    from app.modules.stream.active_playback import (
        clear_active_playbacks,
        record_active_playback,
        wait_for_active_binge_group,
    )

    clear_active_playbacks()
    api_key = "concurrent-key"
    valid_groups = {"ncore-111", "ncore-222"}

    # Párhuzamos várakozás két taszkban
    task1 = asyncio.create_task(
        wait_for_active_binge_group(api_key, valid_groups, timeout=1.0)
    )
    task2 = asyncio.create_task(
        wait_for_active_binge_group(api_key, valid_groups, timeout=1.0)
    )

    await asyncio.sleep(0.01)
    # Stream elindulása
    record_active_playback(api_key, "ncore", "222")

    res1, res2 = await asyncio.gather(task1, task2)
    assert res1 == "ncore-222"
    assert res2 == "ncore-222"
    clear_active_playbacks()


def test_relay_prioritizes_hungarian_subtitles():
    from app.modules.relay.entities import Torrent

    v1 = TorrentFileInfo(
        name="Noragami - 01.mkv",
        path="Noragami/Noragami - 01.mkv",
        size=1000,
        offset=0,
        start_piece_index=0,
        end_piece_index=0,
        is_video=True,
        is_subtitle=False,
        index=0,
    )
    # Angol felirat van elöl a torrentben
    s_eng = TorrentFileInfo(
        name="Noragami - 01.eng.srt",
        path="Noragami/Noragami - 01.eng.srt",
        size=500,
        offset=20000,
        start_piece_index=20,
        end_piece_index=20,
        is_video=False,
        is_subtitle=True,
        index=1,
    )
    # Magyar felirat követi
    s_hun = TorrentFileInfo(
        name="Noragami - 01.hun.srt",
        path="Noragami/Noragami - 01.hun.srt",
        size=500,
        offset=30000,
        start_piece_index=30,
        end_piece_index=30,
        is_video=False,
        is_subtitle=True,
        index=2,
    )

    t_info = TorrentInfo(
        info_hash="hash_lang_prio",
        name="Noragami DualSub",
        size=40000,
        piece_size=1000,
        files=[v1, s_eng, s_hun],
    )

    mock_handle = MagicMock()
    mock_service = MagicMock()

    torrent = Torrent(
        torrent_handle=mock_handle,
        torrent_info=t_info,
        service=mock_service,
        default_priority=0,
    )

    pieces = torrent.files[0].get_matched_subtitle_pieces()
    # A magyar felirat piece-e (30) meg kell jelenjen és előnyt kell élvezzen
    assert 30 in pieces





