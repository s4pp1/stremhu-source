import pytest

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef, IndexerDefinitionRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.parser import parse_torrent_name
from app.modules.media_attributes.tech_info_parser import (
    parse_tech_info_metadata,
)
from app.modules.stremio.schemas import StremioStream
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.torrent_streams.service import (
    _DEFAULT_ATTRIBUTES_MAP,
    TorrentStreamsService,
)


def test_tech_info_parser_english_mediainfo():
    nfo = """
General
Unique ID : 190787360723944789816512595930752695673
Format : Matroska
Duration : 24mn 27s

Video #1
Format : AVC
Duration : 24mn 27s
Language : Japanese

Audio #1
Format : FLAC
Title : [FLAC 2.0]
Language : Japanese

Audio #2
Format : FLAC
Title : [FLAC 5.1]
Language : English

Text #1
Format : ASS
Language : English
    """
    desc = """
<span style="text-decoration:underline">Hangsáv</span>: Japán 2.0 FLAC<br/>
<span style="text-decoration:underline">Feliratok</span>: Angol (Coalgirls), Magyar (CoolTeam Anime)
    """
    meta = parse_tech_info_metadata(nfo_text=nfo, description_text=desc)
    assert "jap" in meta.audio_languages
    assert "eng" in meta.audio_languages
    assert meta.has_hungarian_sub is True


def test_tech_info_parser_hungarian_mediainfo():
    nfo = """
Általános
Formátum : Matroska
Fájlméret : 1,20 GiB

Videó #1
Képméret : 1920x1080

Hang #1
Formátum : FLAC
Nyelv : japán

Hang #2
Formátum : AAC
Nyelv : angol

Szöveg #1
Formátum : ASS
Nyelv : magyar

Szöveg #2
Formátum : ASS
Nyelv : angol
    """
    meta = parse_tech_info_metadata(nfo_text=nfo)
    assert meta.audio_languages == {"jap", "eng"}
    assert meta.has_hungarian_sub is True


def test_tech_info_parser_hungarian_audio_only():
    nfo = """
Audio #1
Language : Hungarian

Text #1
Language : English
    """
    desc = "Hangsáv: Magyar 5.1\nFelirat: Nincs"
    meta = parse_tech_info_metadata(nfo_text=nfo, description_text=desc)
    assert meta.audio_languages == {"hun"}
    assert meta.has_hungarian_sub is False


def test_tech_info_parser_english_only_no_hungarian():
    nfo = """
Audio #1
Language : English

Text #1
Language : English
    """
    desc = "Audio: English DTS-HD\nSubtitles: English SDH"
    meta = parse_tech_info_metadata(nfo_text=nfo, description_text=desc)
    assert meta.audio_languages == {"eng"}
    assert meta.has_hungarian_sub is False


def test_tech_info_parser_empty_and_garbage():
    meta = parse_tech_info_metadata("", "")
    assert meta.audio_languages == set()
    assert meta.has_hungarian_sub is False

    garbage = "Random text with some words <div>table</div> <!-- comment -->"
    meta_garbage = parse_tech_info_metadata(garbage, garbage)
    assert meta_garbage.audio_languages == set()
    assert meta_garbage.has_hungarian_sub is False


def test_japanese_regex_matching_in_seeds():
    # JPN standard code
    attrs = parse_torrent_name("Shingeki.no.Kyojin.S01.720p.BluRay.JPN-AnimeGroup")
    attr_ids = {a.id for a in attrs}
    assert MediaAttributeKey.JAP in attr_ids

    # Dual-Audio
    attrs_dual = parse_torrent_name("Attack.on.Titan.S04.Dual-Audio.1080p.WEBRip")
    attr_ids_dual = {a.id for a in attrs_dual}
    assert MediaAttributeKey.JAP in attr_ids_dual

    # Multi-Audio
    attrs_multi = parse_torrent_name("Death.Note.Complete.Multi.Audio.1080p")
    attr_ids_multi = {a.id for a in attrs_multi}
    assert MediaAttributeKey.JAP in attr_ids_multi

    # Classic japán / japanese
    attrs_jap = parse_torrent_name("Naruto.Shippuuden.Japanese.720p")
    attr_ids_jap = {a.id for a in attrs_jap}
    assert MediaAttributeKey.JAP in attr_ids_jap


def test_stremio_stream_subtitle_badge():
    acc = IndexerAccountModel(
        indexer_id="ncore",
        username="test",
        password="pwd",
        download_full_torrent=False,
    )
    idef = IndexerDefinitionModel(
        id="ncore",
        name="nCore",
        url="https://ncore.pro",
        details_path="/torrents.php?action=details&id={torrent_id}",
    )
    acc.indexer_definition = idef

    jap_attr = _DEFAULT_ATTRIBUTES_MAP[MediaAttributeKey.JAP]

    # Stream WITH Hungarian subtitle
    ts_with_sub = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(acc),
        torrent_id="12345",
        info_hash="hash1",
        torrent_name="Anime S01E01 1080p",
        file_name="Anime_S01E01.mkv",
        file_size=1024 * 1024 * 500,
        file_index=0,
        play_url="https://localhost:7070/play",
        seeders=10,
        attributes=[jap_attr, IndexerDefinitionRef.from_model(idef)],
        has_hungarian_sub=True,
    )

    stremio_stream = StremioStream.from_imdb_torrent_stream(ts_with_sub)
    assert "💬 🇭🇺 Felirat" in stremio_stream.description
    assert "🇯🇵 Jap" in stremio_stream.description

    # Stream WITHOUT Hungarian subtitle
    ts_no_sub = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(acc),
        torrent_id="12345",
        info_hash="hash1",
        torrent_name="Anime S01E01 1080p",
        file_name="Anime_S01E01.mkv",
        file_size=1024 * 1024 * 500,
        file_index=0,
        play_url="https://localhost:7070/play",
        seeders=10,
        attributes=[jap_attr, IndexerDefinitionRef.from_model(idef)],
        has_hungarian_sub=False,
    )

    stremio_stream_no_sub = StremioStream.from_imdb_torrent_stream(ts_no_sub)
    assert "💬 🇭🇺 Felirat" not in stremio_stream_no_sub.description
    assert "🇯🇵 Jap" in stremio_stream_no_sub.description


@pytest.mark.anyio
async def test_enrich_torrent_streams_with_tech_info():
    acc = IndexerAccountModel(
        indexer_id="ncore",
        username="test",
        password="pwd",
        download_full_torrent=False,
    )
    idef = IndexerDefinitionModel(
        id="ncore",
        name="nCore",
        url="https://ncore.pro",
        details_path="/torrents.php?action=details&id={torrent_id}",
    )
    acc.indexer_definition = idef

    eng_fallback = _DEFAULT_ATTRIBUTES_MAP[MediaAttributeKey.ENG]

    # Torrent originally has only false ENG fallback from hdser category
    ts = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(acc),
        torrent_id="812207",
        info_hash="hash_fma",
        torrent_name="Fullmetal Alchemist Brotherhood 720p",
        file_name="FMA_01.mkv",
        file_size=1024 * 1024 * 800,
        file_index=0,
        play_url="https://localhost:7070/play",
        seeders=50,
        attributes=[eng_fallback, IndexerDefinitionRef.from_model(idef)],
        has_hungarian_sub=False,
    )

    class MockIndexerDef:
        async def fetch_tech_info(self, torrent_id: str):
            nfo = """
Audio #1
Language : Japanese

Text #1
Language : English
            """
            desc = "Hangsáv: Japán 2.0 FLAC\nFeliratok: Magyar"
            return nfo, desc

    class MockIndexerDefsService:
        def get_by_id(self, indexer_id: str):
            return MockIndexerDef()

    from unittest.mock import MagicMock
    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
        indexer_definitions_service=MockIndexerDefsService(),  # type: ignore
    )

    enriched = await service._enrich_torrent_streams_with_tech_info([ts])
    assert len(enriched) == 1
    stream = enriched[0]

    attr_ids = {a.id for a in stream.attributes if isinstance(a, MediaAttributeModel)}
    # JAP should be added
    assert MediaAttributeKey.JAP in attr_ids
    # False ENG fallback should be removed (since Tech Info had only Japanese audio)
    assert MediaAttributeKey.ENG not in attr_ids
    # Hungarian sub should be set to True
    assert stream.has_hungarian_sub is True


@pytest.mark.anyio
async def test_fast_path_hungarian_sub_regex():
    from unittest.mock import MagicMock

    acc = IndexerAccountModel(
        indexer_id="ncore",
        username="test",
        password="pwd",
        download_full_torrent=False,
    )
    idef = IndexerDefinitionModel(
        id="ncore",
        name="nCore",
        url="https://ncore.pro",
        details_path="/torrents.php?action=details&id={torrent_id}",
    )
    acc.indexer_definition = idef

    # Release name clearly has HunSub
    ts1 = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(acc),
        torrent_id="99901",
        info_hash="hash_hunsub",
        torrent_name="Shingeki.no.Kyojin.S01E01.HunSub.1080p",
        file_name="ep01.mkv",
        file_size=1024 * 1024 * 500,
        file_index=0,
        play_url="https://localhost:7070/play",
        seeders=10,
        attributes=[IndexerDefinitionRef.from_model(idef)],
        has_hungarian_sub=False,
    )

    # File name has Sub.Hun
    ts2 = TorrentStream(
        indexer_account=IndexerAccountRef.from_model(acc),
        torrent_id="99902",
        info_hash="hash_subhun",
        torrent_name="Anime.Pakk",
        file_name="Episode.01.Sub.Hun.mkv",
        file_size=1024 * 1024 * 500,
        file_index=0,
        play_url="https://localhost:7070/play",
        seeders=10,
        attributes=[IndexerDefinitionRef.from_model(idef)],
        has_hungarian_sub=False,
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
        indexer_definitions_service=MagicMock(),
    )

    enriched = await service._enrich_torrent_streams_with_tech_info([ts1, ts2])
    assert enriched[0].has_hungarian_sub is True
    assert enriched[1].has_hungarian_sub is True
