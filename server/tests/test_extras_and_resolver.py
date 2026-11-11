from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.schemas.internal import SeriesInfo
from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.stremio.catalogs_service import StremioCatalogsService
from app.modules.stremio.constants import SEARCH_ID
from app.modules.stremio.enums import MediaType
from app.modules.stremio.schemas import KitsuStreamId, MalStreamId, ParsedExtra
from app.modules.stremio.tvdb_resolver import TvdbResolver
from app.modules.stremio.utils import parse_stream_id
from app.modules.torrent_streams.utils.resolver_helpers import (
    is_extra_file,
    is_extra_folder,
)
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver


def make_file(
    path: str, index: int, size: int = 1000, is_video: bool = True
) -> TorrentFileInfo:
    name = path.split("/")[-1]
    return TorrentFileInfo(
        name=name,
        path=path,
        size=size,
        offset=index * 1000,
        start_piece_index=index,
        end_piece_index=index,
        is_video=is_video,
        index=index,
    )


def test_extra_folder_and_file_helpers():
    assert is_extra_folder("Extras") is True
    assert is_extra_folder("extras") is True
    assert is_extra_folder("[Extras]") is True
    assert is_extra_folder("00. Extrák") is True
    assert is_extra_folder("00 - Extrák") is True
    assert is_extra_folder("BD Menü") is True
    assert is_extra_folder("DVD Menu") is True
    assert is_extra_folder("Borítók") is True
    assert is_extra_folder("Specials") is True
    assert is_extra_folder("Különkiadások") is True
    assert is_extra_folder("Season 2 Extras") is True
    assert is_extra_folder("S02 Extras") is True
    assert is_extra_folder("SP") is True
    assert is_extra_folder("NCED") is True
    assert is_extra_folder("NCOP") is True
    assert is_extra_folder("OAD") is True
    assert is_extra_folder("OVA") is True
    assert is_extra_folder("Bonus") is True
    assert is_extra_folder("Bónuszok") is True
    assert is_extra_folder("Featurettes") is True
    assert is_extra_folder("Season 1") is False
    assert is_extra_folder("Season 2") is False
    assert is_extra_folder("01. Noragami") is False
    assert is_extra_folder("02. Noragami Aragoto") is False
    assert is_extra_folder("Noragami Aragoto") is False
    assert is_extra_folder("Special A") is False
    assert is_extra_folder("Special Ops") is False

    assert is_extra_file("Noragami Aragoto - Extra 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - SP 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - SP01.mkv") is True
    assert is_extra_file("Noragami Aragoto - OAD 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - OVA 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - NCED 01.mkv") is True
    assert is_extra_file("Noragami Aragoto - NCED.mkv") is True
    assert is_extra_file("Noragami Aragoto - NCOP.mkv") is True
    assert is_extra_file("Noragami Aragoto Menu.mkv") is True
    assert is_extra_file("Noragami Aragoto Menü.mkv") is True
    assert is_extra_file("Noragami Aragoto - 01.mkv") is False
    assert is_extra_file("Special A - 01.mkv") is False


def test_noragami_extras_folder_excluded_for_season_2():
    t_noragami = TorrentInfo(
        info_hash="hash_noragami",
        name="[AnimeRG] Noragami Aragoto S02 [1080p]",
        size=8000,
        piece_size=1000,
        files=[
            make_file(
                "Noragami Aragoto/Extras/Noragami Aragoto Menu.mkv", 0, size=2000
            ),
            make_file("Noragami Aragoto/Extras/01.mkv", 1, size=2500),
            make_file(
                "Noragami Aragoto/Extras/Noragami Aragoto OAD 01.mkv", 2, size=2200
            ),
            make_file(
                "Noragami Aragoto/Noragami Aragoto - 01 [1080p].mkv", 3, size=1500
            ),
            make_file(
                "Noragami Aragoto/Noragami Aragoto - 02 [1080p].mkv", 4, size=1500
            ),
        ],
    )

    resolver_s2e1 = StreamFileResolver(
        t_noragami, series=SeriesInfo(season=2, episode=1)
    )
    resolved_file = resolver_s2e1.resolve()

    assert resolved_file is not None
    assert resolved_file.name == "Noragami Aragoto - 01 [1080p].mkv"

    resolver_s0e1 = StreamFileResolver(
        t_noragami, series=SeriesInfo(season=0, episode=1)
    )
    resolved_special = resolver_s0e1.resolve()
    assert resolved_special is not None
    assert resolved_special.name in (
        "Noragami Aragoto OAD 01.mkv",
        "01.mkv",
    )


def test_noragami_bdbox_real_structure():
    files = [
        make_file("Noragami S01-S02 BDBOX/00. Extrák/BD Menü/S02/Vol 2.mkv", 0, size=2000),
        make_file("Noragami S01-S02 BDBOX/01. Noragami/[ReinForce] Noragami - 01 (BDRip).mkv", 1, size=1500),
        make_file("Noragami S01-S02 BDBOX/01. Noragami/[ReinForce] Noragami OAD1 (DVDRip).mkv", 2, size=1200),
        make_file("Noragami S01-S02 BDBOX/02. Noragami Aragoto/[ReinForce] Noragami Aragoto - 01 (BDRip).mkv", 3, size=1600),
        make_file("Noragami S01-S02 BDBOX/02. Noragami Aragoto/[ReinForce] Noragami Aragoto - 02 (BDRip).mkv", 4, size=1600),
        make_file("Noragami S01-S02 BDBOX/02. Noragami Aragoto/[ReinForce] Noragami Aragoto - 13 (BDRip).mkv", 5, size=1700),
    ]

    t_box = TorrentInfo(
        info_hash="hash_noragami_box",
        name="Noragami S01-S02 BDBOX (BD_1920x1080)",
        size=10000,
        piece_size=1000,
        files=files,
    )

    # Season 2 Episode 1 (alt_episodes=[13])
    r_s2e1 = StreamFileResolver(t_box, series=SeriesInfo(season=2, episode=1, alternate_episodes=[13]))
    v_s2e1 = r_s2e1.resolve()
    assert v_s2e1 is not None
    assert v_s2e1.name == "[ReinForce] Noragami Aragoto - 01 (BDRip).mkv"

    # Season 2 Episode 2 (alt_episodes=[14])
    r_s2e2 = StreamFileResolver(t_box, series=SeriesInfo(season=2, episode=2, alternate_episodes=[14]))
    v_s2e2 = r_s2e2.resolve()
    assert v_s2e2 is not None
    assert v_s2e2.name == "[ReinForce] Noragami Aragoto - 02 (BDRip).mkv"

    # Season 1 Episode 1
    r_s1e1 = StreamFileResolver(t_box, series=SeriesInfo(season=1, episode=1))
    v_s1e1 = r_s1e1.resolve()
    assert v_s1e1 is not None
    assert v_s1e1.name == "[ReinForce] Noragami - 01 (BDRip).mkv"

    # Specials
    r_s0e1 = StreamFileResolver(t_box, series=SeriesInfo(season=0, episode=1))
    v_s0e1 = r_s0e1.resolve()
    assert v_s0e1 is not None
    assert v_s0e1.name == "[ReinForce] Noragami OAD1 (DVDRip).mkv"



@pytest.mark.anyio
async def test_resolve_tmdb_wikidata_mock():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": {
            "bindings": [
                {
                    "imdb": {"value": "tt15239678"},
                    "labelHu": {"value": "Dűne: Második rész"},
                    "labelEn": {"value": "Dune: Part Two"},
                }
            ]
        }
    }
    mock_client.get.return_value = mock_resp
    resolver._client = mock_client

    imdb_id, title = await resolver.resolve_tmdb("693134", is_series=False)
    assert imdb_id == "tt15239678"
    assert title == "Dűne: Második rész"
    assert resolver._cache.get("title_tt15239678") == "Dűne: Második rész"


@pytest.mark.anyio
async def test_resolve_tmdb_web_scraping_fallback():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_client.is_closed = False

    # Wikidata returns 404 or empty
    mock_wiki_resp = MagicMock()
    mock_wiki_resp.status_code = 404

    # Web returns HTML
    mock_web_resp = MagicMock()
    mock_web_resp.status_code = 200
    mock_web_resp.text = (
        '<html><head><meta property="og:title" content="A visszavágó - Kapj el, ha tudsz!" /></head>'
        '<body><p><strong>Eredeti cím</strong> A visszavágó</p></body></html>'
    )

    async def fake_get(url, **kwargs):
        if "wikidata.org" in url:
            return mock_wiki_resp
        return mock_web_resp

    mock_client.get.side_effect = fake_get
    resolver._client = mock_client

    imdb_id, title = await resolver.resolve_tmdb("999999", is_series=True)
    assert imdb_id is None
    assert title == "A visszavágó - Kapj el, ha tudsz!"


@pytest.mark.anyio
async def test_stremio_catalog_service_supports_series():
    mock_torrent_files = MagicMock()
    mock_provider = AsyncMock()
    mock_isolated = MagicMock()

    service = StremioCatalogsService(
        torrent_files_service=mock_torrent_files,
        torrent_source_provider_service=mock_provider,
        isolated_torrent_files_service=mock_isolated,
    )

    # Series search with t-12345
    mock_source = MagicMock()
    mock_source.torrent_file.indexer_id = "ncore"
    mock_source.torrent_file.torrent_id = "12345"
    mock_source.torrent_file.info.name = "Test Series S01"
    mock_provider.find_by_torrent_id.return_value = ([mock_source], [])

    res = await service.get_catalog(
        media_type=MediaType.SERIES,
        catalog_id=SEARCH_ID,
        extra=ParsedExtra(search="t-12345"),
    )
    assert len(res.metas) == 1
    assert res.metas[0].id == "stremhu-source:ncore:12345"


def test_parse_stream_id_mal_and_anime_prefixes():
    # MAL stream IDs
    mal_stream = parse_stream_id("mal:21:1")
    assert isinstance(mal_stream, MalStreamId)
    assert mal_stream.mal_id == "21"
    assert mal_stream.episode == 1

    # anime: prefix stripped
    anime_kitsu = parse_stream_id("anime:kitsu:12:3")
    assert isinstance(anime_kitsu, KitsuStreamId)
    assert anime_kitsu.kitsu_id == "12"
    assert anime_kitsu.episode == 3

    anime_mal = parse_stream_id("anime:mal:100:2")
    assert isinstance(anime_mal, MalStreamId)
    assert anime_mal.mal_id == "100"
    assert anime_mal.episode == 2


@pytest.mark.anyio
async def test_resolve_tvdb_series_via_tvmaze():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_client.is_closed = False

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "name": "Game of Thrones",
        "externals": {"imdb": "tt0944947"},
    }
    mock_client.get.return_value = mock_resp
    resolver._client = mock_client

    imdb_id, title = await resolver.resolve_tvdb("121361", is_series=True)
    assert imdb_id == "tt0944947"
    assert title == "Game of Thrones"


@pytest.mark.anyio
async def test_resolve_tvdb_movie_via_wikidata():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_client.is_closed = False

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": {
            "bindings": [
                {
                    "imdb": {"value": "tt1375666"},
                    "labelHu": {"value": "Eredet"},
                    "labelEn": {"value": "Inception"},
                }
            ]
        }
    }
    mock_client.get.return_value = mock_resp
    resolver._client = mock_client

    imdb_id, title = await resolver.resolve_tvdb("305", is_series=False)
    assert imdb_id == "tt1375666"
    assert title == "Eredet"


@pytest.mark.anyio
async def test_resolve_kitsu_with_title_fallback():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_client.is_closed = False

    # strem.fun returns 404
    mock_404 = MagicMock()
    mock_404.status_code = 404

    # kitsu API returns canonicalTitle
    mock_kitsu = MagicMock()
    mock_kitsu.status_code = 200
    mock_kitsu.json.return_value = {
        "data": {
            "attributes": {
                "canonicalTitle": "Solo Leveling",
                "titles": {"en": "Solo Leveling"},
            }
        }
    }

    async def fake_get(url, **kwargs):
        if "kitsu.io" in url:
            return mock_kitsu
        return mock_404

    mock_client.get.side_effect = fake_get
    resolver._client = mock_client

    imdb_id, season, ep, alt_eps, alt_seasons, title = await resolver.resolve_kitsu(45678, 1)
    assert imdb_id is None
    assert season == 1
    assert ep == 1
    assert title == "Solo Leveling"


@pytest.mark.anyio
async def test_resolve_mal_via_kitsu_mapping():
    resolver = TvdbResolver()
    mock_client = AsyncMock()
    mock_client.is_closed = False

    # 1. Kitsu mapping returns kitsu item id 12
    mock_mapping_resp = MagicMock()
    mock_mapping_resp.status_code = 200
    mock_mapping_resp.json.return_value = {
        "data": [
            {
                "relationships": {
                    "item": {"data": {"type": "anime", "id": "12"}}
                }
            }
        ]
    }

    # 2. Kitsu details
    mock_kitsu_resp = MagicMock()
    mock_kitsu_resp.status_code = 200
    mock_kitsu_resp.json.return_value = {
        "data": {
            "attributes": {
                "canonicalTitle": "One Piece",
                "titles": {"en": "One Piece"},
            }
        }
    }

    # 3. strem.fun returns imdb_id in meta
    mock_stremfun_resp = MagicMock()
    mock_stremfun_resp.status_code = 200
    mock_stremfun_resp.json.return_value = {
        "meta": {
            "imdb_id": "tt0388629",
            "name": "One Piece",
        }
    }

    async def fake_get(url, **kwargs):
        if "mappings" in url:
            return mock_mapping_resp
        if "kitsu.io/api/edge/anime" in url:
            return mock_kitsu_resp
        if "strem.fun" in url:
            return mock_stremfun_resp
        return MagicMock(status_code=404)

    mock_client.get.side_effect = fake_get
    resolver._client = mock_client

    imdb_id, season, ep, alt_eps, alt_seasons, title = await resolver.resolve_mal("21", 1)
    assert imdb_id == "tt0388629"
    assert title == "One Piece"


