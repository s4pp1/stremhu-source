from unittest.mock import MagicMock

import pytest

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.relay.entities import File
from app.modules.stremio.schemas import StremioStream
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.torrent_streams.service import TorrentStreamsService


def _create_mock_indexer(indexer_id: str, indexer_name: str) -> IndexerAccountRef:
    definition = IndexerDefinitionModel(
        id=indexer_id,
        name=indexer_name,
        url=f"https://{indexer_id}.invalid",
        details_path="/details",
    )
    account = IndexerAccountModel(
        indexer_id=indexer_id,
        username="teszt",
        password="teszt",
    )
    account.indexer_definition = definition
    return IndexerAccountRef.from_model(account)


def test_deduplicate_torrent_streams_by_info_hash():
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")

    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="aabbcc112233",
        seeders=45,
        torrent_name="Inception.2010.1080p.BluRay.x264.HUN-TRiNiTY",
        attributes=[],
        file_name="inception.mkv",
        file_size=10_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/1",
        is_persisted_torrent=False,
    )

    stream2 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t2",
        info_hash="aabbcc112233",  # ugyanaz a hash
        seeders=30,
        torrent_name="Inception.2010.1080p.BluRay.x264.HUN-TRiNiTY",
        attributes=[],
        file_name="inception.mkv",
        file_size=10_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/2",
        is_persisted_torrent=True,  # HunTorrenten letöltve/cache-elve van
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams([stream1, stream2])

    assert len(deduped) == 1
    result = deduped[0]
    assert result.info_hash == "aabbcc112233"
    assert "nCore" in result.extra_indexer_names
    assert "HunTorrent" in result.extra_indexer_names
    assert result.combined_seeders == 75  # 45 + 30
    assert result.is_persisted_torrent is True


def test_deduplicate_torrent_streams_by_name_and_size_fallback():
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")

    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="",  # Nincs info_hash
        seeders=20,
        torrent_name="Oppenheimer.2023.1080p.HUN.mkv",
        attributes=[],
        file_name="Oppenheimer.2023.1080p.HUN.mkv",
        file_size=8_589_934_592,  # 8 GB
        file_index=0,
        play_url="http://localhost:7070/play/1",
    )

    stream2 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t2",
        info_hash="",  # Nincs info_hash
        seeders=15,
        torrent_name="Oppenheimer.2023.1080p.HUN.mkv",
        attributes=[],
        file_name="Oppenheimer.2023.1080p.HUN.mkv",
        file_size=8_589_934_592,
        file_index=0,
        play_url="http://localhost:7070/play/2",
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams([stream1, stream2])

    assert len(deduped) == 1
    result = deduped[0]
    assert "nCore" in result.extra_indexer_names
    assert "HunTorrent" in result.extra_indexer_names
    assert result.combined_seeders == 35


def test_deduplicate_different_file_index_not_merged():
    """M04: Azonos info_hash de eltérő file_index (pl. Episode 1 vs Episode 2) nem vonható össze!"""
    ncore_acc = _create_mock_indexer("ncore", "nCore")

    ep1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="aabbcc112233",
        seeders=45,
        torrent_name="Anime.Series.S01.1080p",
        attributes=[],
        file_name="Anime.S01E01.mkv",
        file_size=1_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/1/0",
    )
    ep2 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="aabbcc112233",
        seeders=45,
        torrent_name="Anime.Series.S01.1080p",
        attributes=[],
        file_name="Anime.S01E02.mkv",
        file_size=1_000_000_000,
        file_index=1,
        play_url="http://localhost:7070/play/1/1",
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams([ep1, ep2])
    assert len(deduped) == 2
    assert {s.file_index for s in deduped} == {0, 1}


def test_deduplicate_different_info_hash_not_merged():
    """M04: Eltérő info_hash esetén a fájlok nem vonhatók össze, külön találatként maradnak meg."""
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")

    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="hash1111111111",
        seeders=50,
        torrent_name="Movie.2024.1080p",
        attributes=[],
        file_name="Movie.2024.1080p.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/t1/0",
    )
    stream2 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t2",
        info_hash="hash2222222222",
        seeders=30,
        torrent_name="Movie.2024.1080p",
        attributes=[],
        file_name="Movie.2024.1080p.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/t2/0",
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams([stream1, stream2])
    assert len(deduped) == 2
    assert {s.info_hash for s in deduped} == {"hash1111111111", "hash2222222222"}


def test_deduplicate_preserves_downloaded_source_url():
    """M04: Forráskonzisztencia - a letöltött találat URL-je és állapota érvényesül."""
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")

    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="commonhash123",
        seeders=50,
        torrent_name="Movie.2024.1080p",
        attributes=[],
        file_name="Movie.2024.1080p.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/ncore/stream",
        is_persisted_torrent=False,
    )
    stream2 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t2",
        info_hash="commonhash123",
        seeders=30,
        torrent_name="Movie.2024.1080p",
        attributes=[],
        file_name="Movie.2024.1080p.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/huntorrent/downloaded_stream",
        is_persisted_torrent=True,  # HunTorrenten helyben letöltve
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams([stream1, stream2])
    assert len(deduped) == 1
    assert deduped[0].is_persisted_torrent is True
    # A play_url garantáltan a letöltött forráshoz vezet
    assert deduped[0].play_url == "http://localhost:7070/play/huntorrent/downloaded_stream"


def test_stremio_stream_formatting_and_flags():
    ncore_acc = _create_mock_indexer("ncore", "nCore")

    hun_attr = MediaAttributeModel(
        id="hun",
        preference_id="language",
        name="Magyar",
        short_name="Hun",
    )
    eng_attr = MediaAttributeModel(
        id="eng",
        preference_id="language",
        name="Angol",
        short_name="Eng",
    )
    res_attr = MediaAttributeModel(
        id="1080p",
        preference_id="resolution",
        name="1080p",
        short_name="1080p",
    )

    stream = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="11223344",
        seeders=50,
        torrent_name="Interstellar.2014.1080p.HUN.ENG.x264",
        attributes=[res_attr, hun_attr, eng_attr],
        file_name="Interstellar.mkv",
        file_size=12_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/interstellar",
        is_persisted_torrent=True,
        extra_indexer_names=["nCore", "HunTorrent"],
        combined_seeders=85,
    )

    stremio_stream = StremioStream.from_imdb_torrent_stream(stream)

    # 1. Címben ott kell legyen a letöltött jelzés, de [StremHU] prefix nélkül
    assert "[StremHU]" not in stremio_stream.name
    assert "⚡ Letöltve" in stremio_stream.name
    assert "1080p" in stremio_stream.name

    # 2. Leírásban: Letöltve státusz legfelül
    assert "⚡ Helyben tárolva (Azonnali lejátszás)" in stremio_stream.description

    # 3. Zászlók a nyelveknél
    assert "🇭🇺 Hun" in stremio_stream.description
    assert "🇬🇧 Eng" in stremio_stream.description

    # 4. Összevont trackerek és seederek
    assert "🧲 nCore, HunTorrent" in stremio_stream.description
    assert "👥 85" in stremio_stream.description


def test_relay_file_boundary_priorities():
    torrent_mock = MagicMock()
    torrent_mock.piece_size = 1024 * 1024  # 1 MB pieces

    # 10 darab 1MB-os darabból álló fájl (start=0, end=9)
    file_info_mock = MagicMock()
    file_info_mock.name = "movie.mkv"
    file_info_mock.size = 10 * 1024 * 1024
    file_info_mock.offset = 0

    file = File(file_info_mock, torrent_mock)
    assert file.start_piece_index == 0
    assert file.end_piece_index == 9

    torrent_mock.torrent_handle = MagicMock()
    # Tegyük fel, hogy a 0. és 9. darab már megvan, de az 1., 2. és 7., 8. még hiányzik
    torrent_mock.torrent_handle.have_piece.side_effect = lambda p: p in (0, 9)

    target_deadlines: dict[int, int] = {}
    torrent_mock._set_file_boundary_priorities = (
        lambda f, d: Torrent._set_file_boundary_priorities(torrent_mock, f, d)
    )

    from app.modules.relay.entities import Torrent

    Torrent._set_file_boundary_priorities(torrent_mock, file, target_deadlines)

    # boundary_count = min(3, 10 // 2) = 3
    # Eleje: 0 (have_piece=True), 1 (deadline=0), 2 (deadline=0)
    # Vége: 9 (have_piece=True), 8 (deadline=0), 7 (deadline=0)
    assert 0 not in target_deadlines
    assert target_deadlines.get(1) == 0
    assert target_deadlines.get(2) == 0
    assert target_deadlines.get(7) == 0
    assert target_deadlines.get(8) == 0
    assert 9 not in target_deadlines


def test_fallback_queries_series_prioritization():
    from app.common.schemas.internal import SeriesInfo

    series = SeriesInfo(season=4, episode=1)
    queries = TorrentStreamsService._build_fallback_queries("Stranger Things", series=series)

    # A specifikus évados lekérdezéseknek meg kell előzniük az általános címet
    assert "Stranger Things S04" in queries
    assert "Stranger Things S04E01" in queries
    s04_idx = queries.index("Stranger Things S04")
    general_idx = queries.index("Stranger Things")
    assert s04_idx < general_idx


def test_deduplicate_seeders_calculation_exact():
    """
    M04 követelményváltozás:
    A multi-tracker és cross-seed seeder összesítéshez azonos info_hash és file_index szükséges.
    Eltérő info_hash esetén a torrentek önálló streamként maradnak meg.
    Itt ugyanaz a torrent (info_hash='common_naruto_hash') több indexeren szerepel különböző seeder számokkal.
    """
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")
    majom_acc = _create_mock_indexer("majomparade", "Majomparádé")

    # 5 MB-os anime epizód
    file_size = 5_000_000
    clean_name = "naruto_ep01.mkv"
    common_hash = "common_naruto_hash"

    # 1. nCore release: 100 seeder
    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash=common_hash,
        seeders=100,
        torrent_name="Naruto.Ep01.1080p",
        attributes=[],
        file_name=clean_name,
        file_size=file_size,
        file_index=0,
        play_url="http://localhost:7070/play/1",
    )

    # 2. nCore másik duplikált release ugyanazzal a hash-sel: 80 seeder (nem szabad hozzáadni a 100-hoz, a max marad 100)
    stream2 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t2",
        info_hash=common_hash,
        seeders=80,
        torrent_name="Naruto.Ep01.1080p.Dup",
        attributes=[],
        file_name=clean_name,
        file_size=file_size,
        file_index=0,
        play_url="http://localhost:7070/play/2",
    )

    # 3. HunTorrent release: 50 seeder (össze kell adódnia: 100 + 50 = 150)
    stream3 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t3",
        info_hash=common_hash,
        seeders=50,
        torrent_name="Naruto.Ep01.1080p.HT",
        attributes=[],
        file_name=clean_name,
        file_size=file_size,
        file_index=0,
        play_url="http://localhost:7070/play/3",
    )

    # 4. Majomparádé release: 30 seeder (összeadódik: 150 + 30 = 180)
    stream4 = TorrentStream(
        indexer_account=majom_acc,
        torrent_id="t4",
        info_hash=common_hash,
        seeders=30,
        torrent_name="Naruto.Ep01.1080p.MP",
        attributes=[],
        file_name=clean_name,
        file_size=file_size,
        file_index=0,
        play_url="http://localhost:7070/play/4",
    )

    # 5. Újabb HunTorrent release: 70 seeder (frissíti a HunTorrentet 50 -> 70-re, új összeg: 100 + 70 + 30 = 200)
    stream5 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t5",
        info_hash=common_hash,
        seeders=70,
        torrent_name="Naruto.Ep01.1080p.HT2",
        attributes=[],
        file_name=clean_name,
        file_size=file_size,
        file_index=0,
        play_url="http://localhost:7070/play/5",
    )

    service = TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=MagicMock(),
        torrents_service=MagicMock(),
        settings_service=MagicMock(),
        preferences_service=MagicMock(),
    )

    deduped = service._deduplicate_torrent_streams(
        [stream1, stream2, stream3, stream4, stream5]
    )

    assert len(deduped) == 1
    res = deduped[0]
    assert res.combined_seeders == 200
    assert "nCore" in res.extra_indexer_names
    assert "HunTorrent" in res.extra_indexer_names
    assert "Majomparádé" in res.extra_indexer_names


def test_is_file_downloaded_series_progress():
    from app.modules.relay.service import RelayService

    service = RelayService.__new__(RelayService)
    service._torrents = {}

    # Mock torrent handle és Torrent entity
    torrent_entity = MagicMock()
    torrent_handle = MagicMock()
    torrent_entity.torrent_handle = torrent_handle

    import libtorrent
    sha1 = libtorrent.sha1_hash(bytes.fromhex("0123456789abcdef0123456789abcdef01234567"))
    service._torrents[sha1] = torrent_entity

    status_mock = MagicMock()
    torrent_handle.status.return_value = status_mock

    # 1. eset: A teljes torrent kész (seeding) -> mindig True
    status_mock.is_seeding = True
    assert service.is_file_downloaded("0123456789abcdef0123456789abcdef01234567", 0, 1000) is True

    # 2. eset: Nem kész, ritka letöltés alatt áll
    status_mock.is_seeding = False
    # File 0: 2 GB kész, File 1: 500 MB (1 GB-ból, félkész), File 2: 0 MB kész (még nem nézett 3. rész)
    torrent_handle.file_progress.return_value = [2_000_000_000, 500_000_000, 0]

    # File 0 kész: 2 GB >= 2 GB -> True
    assert service.is_file_downloaded("0123456789abcdef0123456789abcdef01234567", 0, 2_000_000_000) is True

    # File 1 félkész: 500 MB < 1 GB -> False
    assert service.is_file_downloaded("0123456789abcdef0123456789abcdef01234567", 1, 1_000_000_000) is False

    # File 2 (3. rész a sorozatból) letöltetlen: 0 < 2 GB -> False! (kiküszöböli a fals 'Letöltve' jelzést)
    assert service.is_file_downloaded("0123456789abcdef0123456789abcdef01234567", 2, 2_000_000_000) is False


def test_japanese_language_attribute_detection():
    from app.modules.media_attributes.constants import MediaAttributeKey
    from app.modules.media_attributes.parser import parse_torrent_name
    from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES

    attrs = parse_torrent_name("Attack.on.Titan.S04E01.1080p.JAP.DUB.x264", DEFAULT_ATTRIBUTES)
    attr_ids = [a.id for a in attrs]
    assert MediaAttributeKey.JAP in attr_ids

    # Formázás ellenőrzése
    jap_attr = next(a for a in attrs if a.id == MediaAttributeKey.JAP)
    ncore_acc = _create_mock_indexer("ncore", "nCore")
    stream = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="aabbcc",
        seeders=10,
        torrent_name="Attack on Titan",
        attributes=[jap_attr],
        file_name="aot.mkv",
        file_size=500_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/aot",
    )
    stremio_stream = StremioStream.from_imdb_torrent_stream(stream)
    assert "🇯🇵 Jap" in stremio_stream.description


@pytest.mark.anyio
async def test_user_stream_deduplication_toggle():
    from unittest.mock import AsyncMock, patch

    from app.modules.users.models import UserModel

    ncore_acc = _create_mock_indexer("ncore", "nCore")
    huntorrent_acc = _create_mock_indexer("huntorrent", "HunTorrent")

    stream1 = TorrentStream(
        indexer_account=ncore_acc,
        torrent_id="t1",
        info_hash="hash_dedup_1",
        seeders=40,
        torrent_name="Matrix.1999.1080p",
        attributes=[],
        file_name="matrix.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/1",
    )
    stream2 = TorrentStream(
        indexer_account=huntorrent_acc,
        torrent_id="t2",
        info_hash="hash_dedup_1",
        seeders=30,
        torrent_name="Matrix.1999.1080p",
        attributes=[],
        file_name="matrix.mkv",
        file_size=5_000_000_000,
        file_index=0,
        play_url="http://localhost:7070/play/2",
    )

    mock_provider = AsyncMock()
    mock_src1 = MagicMock()
    mock_src2 = MagicMock()
    mock_provider.find_by_imdb_id.return_value = ([mock_src1, mock_src2], [])

    mock_settings = AsyncMock()
    mock_settings.get_app_url.return_value = "http://localhost:7070"

    mock_torrents = MagicMock()
    mock_torrents.get_torrents.return_value = []

    service = TorrentStreamsService(
        db=AsyncMock(),
        torrent_source_provider_service=mock_provider,
        torrents_service=mock_torrents,
        settings_service=mock_settings,
        preferences_service=MagicMock(),
    )

    # 1. Bekapcsolt deduplikáció esetén (alapértelmezett): 1 darab összevont stream
    with patch.object(TorrentStream, "from_imdb_id", side_effect=[stream1, stream2]):
        user_enabled = UserModel(
            id="u1", username="test1", enable_smart_filter=False, enable_stream_deduplication=True
        )
        user_enabled.preference_definitions = []
        streams, _ = await service.find_by_imdb(user=user_enabled, imdb_id="tt0133093")
        assert len(streams) == 1
        assert streams[0].combined_seeders == 70

    # 2. Kikapcsolt deduplikáció esetén: mindkét stream külön megjelenik
    with patch.object(TorrentStream, "from_imdb_id", side_effect=[stream1, stream2]):
        user_disabled = UserModel(
            id="u2", username="test2", enable_smart_filter=False, enable_stream_deduplication=False
        )
        user_disabled.preference_definitions = []
        streams_disabled, _ = await service.find_by_imdb(user=user_disabled, imdb_id="tt0133093")
        assert len(streams_disabled) == 2
        assert streams_disabled[0].info_hash == "hash_dedup_1"
        assert streams_disabled[1].info_hash == "hash_dedup_1"
