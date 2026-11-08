"""A „⚡ Letöltve” jelölő: fájlszintű állapot, rendezés, megjelenítés és a felhasználói preferencia."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import libtorrent
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.me.schemas.api import MeUpdateRequest
from app.modules.relay.service import RelayService
from app.modules.stremio.schemas import (
    DOWNLOADED_BANNER,
    DOWNLOADED_MARKER,
    StremioStream,
    TorrentStreamId,
)
from app.modules.stremio.service import StremioService, invalidate_stream_cache
from app.modules.torrent_streams.schemas import TorrentStream
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.users.schemas.api import UserResponse
from app.modules.users.schemas.internal import UserCreate, UserUpdate

SERVER_DIR = Path(__file__).resolve().parent.parent
PACK = "0123456789abcdef0123456789abcdef01234567"
SEEDING = "89abcdef0123456789abcdef0123456789abcdef"
NOT_IN_RELAY = "fedcba9876543210fedcba9876543210fedcba98"
GIB = 1024**3


def _account() -> IndexerAccountRef:
    # TorrentStream carries a Session-free frozen reference (CR17), not the ORM account.
    definition = IndexerDefinitionModel(
        id="ncore", name="nCore", url="https://ncore.invalid", details_path="/d"
    )
    account = IndexerAccountModel(indexer_id="ncore", username="x", password="x")
    account.indexer_definition = definition
    return IndexerAccountRef.from_model(account)


def _stream(info_hash: str, file_index: int, seeders: int) -> TorrentStream:
    return TorrentStream(
        indexer_account=_account(),
        torrent_id=f"{info_hash[:4]}-{file_index}",
        info_hash=info_hash,
        torrent_name="Sorozat.S01.1080p",
        file_name=f"Sorozat.S01E0{file_index + 1}.mkv",
        file_size=GIB,
        file_index=file_index,
        play_url=f"https://app.invalid/play/{info_hash[:4]}/{file_index}",
        seeders=seeders,
    )


def _relay(entries: dict[str, dict], handles: dict[str, MagicMock] | None = None) -> RelayService:
    """Valódi RelayService állapotlekérdezés libtorrent-handle csonkokkal."""
    relay = RelayService.__new__(RelayService)
    relay._torrents = {}
    for info_hash, state in entries.items():
        handle = MagicMock()
        handle.is_valid.return_value = state.get("valid", True)
        handle.status.return_value = SimpleNamespace(is_seeding=state.get("seeding", False))
        if state.get("raises"):
            handle.file_progress.side_effect = RuntimeError("libtorrent hiba")
        else:
            handle.file_progress.return_value = state.get("progress", [])
        torrent = MagicMock()
        torrent.torrent_handle = handle
        relay._torrents[libtorrent.sha1_hash(bytes.fromhex(info_hash))] = torrent
        if handles is not None:
            handles[info_hash] = handle
    return relay


def _service(relay: RelayService, **kwargs) -> TorrentStreamsService:
    torrents = SimpleNamespace(
        _relay_service=relay, is_file_downloaded=relay.is_file_downloaded
    )
    return TorrentStreamsService(
        db=MagicMock(),
        torrent_source_provider_service=kwargs.get("provider", MagicMock()),
        torrents_service=torrents,  # type: ignore[arg-type]
        settings_service=kwargs.get("settings", MagicMock()),
        preferences_service=MagicMock(),
    )


def _user(enable_downloaded_marker: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        preference_definitions=[], enable_downloaded_marker=enable_downloaded_marker
    )


def _state(streams: list[TorrentStream]) -> list[tuple[str, int, bool]]:
    return [(s.info_hash[:4], s.file_index, s.is_persisted_torrent) for s in streams]


def test_partial_season_pack_marks_only_completed_episodes_and_lists_them_first():
    # 1. rész kész, 2. félig, 3. el sem kezdődött; a kész rész a legkevesebb seederrel is előre kerül
    relay = _relay({PACK: {"progress": [GIB, GIB // 2, 0]}})
    streams = [_stream(PACK, 1, 50), _stream(PACK, 2, 40), _stream(PACK, 0, 1)]

    result = _service(relay)._sort_torrent_streams(streams, _user())  # type: ignore[arg-type]

    assert _state(result) == [
        ("0123", 0, True),
        ("0123", 1, False),
        ("0123", 2, False),
    ]


def test_seeding_torrent_marks_every_file_without_reading_file_progress():
    handles: dict[str, MagicMock] = {}
    relay = _relay({SEEDING: {"seeding": True}}, handles)
    streams = [_stream(SEEDING, 0, 1), _stream(SEEDING, 1, 1)]

    result = _service(relay)._sort_torrent_streams(streams, _user())  # type: ignore[arg-type]

    assert all(s.is_persisted_torrent for s in result)
    handles[SEEDING].file_progress.assert_not_called()


@pytest.mark.parametrize(
    "entries",
    [
        {},  # a torrent nincs a relayben
        {PACK: {"valid": False, "progress": [GIB]}},  # érvénytelen handle
        {PACK: {"raises": True}},  # a libtorrent-lekérdezés hibát dob
    ],
)
def test_missing_or_unreadable_relay_state_is_not_marked(entries):
    result = _service(_relay(entries))._sort_torrent_streams(
        [_stream(PACK, 0, 1)],
        _user(),  # type: ignore[arg-type]
    )

    assert result[0].is_persisted_torrent is False


def test_disabled_preference_orders_by_seeders_but_keeps_the_real_state():
    relay = _relay({PACK: {"progress": [GIB, 0]}})
    downloaded, popular = _stream(PACK, 0, 1), _stream(NOT_IN_RELAY, 0, 99)

    result = _service(relay)._sort_torrent_streams(
        [downloaded, popular],
        _user(enable_downloaded_marker=False),  # type: ignore[arg-type]
    )

    # Nincs előresorolás, de az állapot megmarad (a deduplikáció a helyi forrást választja)
    assert result == [popular, downloaded]
    assert downloaded.is_persisted_torrent is True


def test_imdb_stream_shows_marker_only_when_downloaded_and_enabled():
    stream = _stream(PACK, 0, 1)
    stream.is_persisted_torrent = True

    shown = StremioStream.from_imdb_torrent_stream(stream, show_downloaded_marker=True)
    hidden = StremioStream.from_imdb_torrent_stream(stream, show_downloaded_marker=False)
    stream.is_persisted_torrent = False
    not_downloaded = StremioStream.from_imdb_torrent_stream(stream)

    assert shown.name.startswith(DOWNLOADED_MARKER)
    assert shown.description.startswith(DOWNLOADED_BANNER)
    for result in (hidden, not_downloaded):
        assert "⚡" not in result.name and "⚡" not in result.description


def test_torrent_id_stream_shows_marker_only_when_downloaded_and_enabled():
    stream = _stream(PACK, 0, 1)
    stream.is_persisted_torrent = True

    shown = StremioStream.from_id_torrent_stream(stream, show_downloaded_marker=True)
    hidden = StremioStream.from_id_torrent_stream(stream, show_downloaded_marker=False)

    assert shown.name.startswith(f"{DOWNLOADED_MARKER} | 💾")
    assert shown.description == f"{DOWNLOADED_BANNER}\n📁 {stream.file_name}"
    assert hidden.name.startswith("💾")
    assert hidden.description == f"📁 {stream.file_name}"


@pytest.mark.anyio
async def test_catalog_torrent_file_list_reports_downloaded_files(monkeypatch):
    # A katalógusból megnyitott torrent fájllistája korábban mindig „nem letöltött” volt
    relay = _relay({PACK: {"progress": [GIB, 0]}})
    provider = MagicMock()
    provider.find_one_by_indexer = AsyncMock(
        return_value=SimpleNamespace(indexer_torrent=None, torrent_file=None)
    )
    settings = MagicMock()
    settings.get_app_url.return_value = "https://app.invalid"
    files = [_stream(PACK, 0, 1), _stream(PACK, 1, 1)]
    monkeypatch.setattr(TorrentStream, "from_torrent_id", lambda **_: files)

    result = await _service(relay, provider=provider, settings=settings).find_by_torrent_id(
        indexer_id="ncore", torrent_id="1", user=_user()  # type: ignore[arg-type]
    )

    assert _state(result) == [("0123", 0, True), ("0123", 1, False)]


@pytest.mark.anyio
async def test_toggling_the_preference_is_not_served_from_the_stream_cache(monkeypatch):
    invalidate_stream_cache()
    service = StremioService(torrent_streams_service=MagicMock(), settings_service=MagicMock())

    fetched: list[bool] = []

    async def uncached(user, parsed_id):
        fetched.append(user.enable_downloaded_marker)
        flag = "be" if user.enable_downloaded_marker else "ki"
        return [StremioStream(name=flag, description="", url="https://app.invalid/x")]

    monkeypatch.setattr(service, "_get_streams_uncached", uncached)
    parsed_id = TorrentStreamId(indexer_id="ncore", torrent_id="1")

    def user(flag: bool) -> SimpleNamespace:
        return SimpleNamespace(
            id="u1",
            api_key="k",
            enable_stream_deduplication=True,
            enable_fallback_subtitles=False,
            enable_smart_filter=False,
            smart_filter_limit=1,
            enable_downloaded_marker=flag,
        )

    try:
        first = await service.get_streams(user(True), parsed_id)  # type: ignore[arg-type]
        second = await service.get_streams(user(False), parsed_id)  # type: ignore[arg-type]
        again = await service.get_streams(user(False), parsed_id)  # type: ignore[arg-type]
    finally:
        invalidate_stream_cache()

    assert [s.name for s in first] == ["be"]
    assert [s.name for s in second] == ["ki"]
    assert [s.name for s in again] == ["ki"]
    # Both settings were fetched; only the repeated request with the same setting came from the cache.
    assert fetched == [True, False]


def test_preference_round_trips_through_the_user_api_schemas():
    payload = MeUpdateRequest.model_validate({"enableDownloadedMarker": False})
    update = UserUpdate(**payload.model_dump(exclude_unset=True))

    assert update.model_dump(exclude_unset=True) == {"enable_downloaded_marker": False}
    assert UserCreate(username="uj").enable_downloaded_marker is True

    user = SimpleNamespace(
        id="u1",
        username="u",
        role=SimpleNamespace(id="user", name="User"),
        api_key="k",
        updated_at="2026-11-08T00:00:00Z",
        created_at="2026-11-08T00:00:00Z",
        torrent_seed=None,
        enable_smart_filter=False,
        enable_stream_deduplication=True,
        smart_filter_grouping_preference_id=None,
        smart_filter_limit=1,
        enable_fallback_subtitles=False,
        enable_catalog_search=True,
        enable_downloaded_marker=False,
        max_concurrent_streams=None,
    )
    response = UserResponse.model_validate(user).model_dump(by_alias=True)
    assert response["enableDownloadedMarker"] is False


def _migration_module():
    path = SERVER_DIR / "alembic/versions/a7c41e9b2d10_add_enable_downloaded_marker_to_users.py"
    spec = importlib.util.spec_from_file_location("downloaded_marker_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_enables_the_marker_for_existing_users_and_is_reversible():
    migration = _migration_module()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE users (id VARCHAR PRIMARY KEY)")
        connection.exec_driver_sql("INSERT INTO users (id) VALUES ('meglevo')")
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        value = connection.exec_driver_sql(
            "SELECT enable_downloaded_marker FROM users WHERE id = 'meglevo'"
        ).scalar()
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        columns = {c["name"] for c in sa.inspect(connection).get_columns("users")}

    assert value == 1
    assert "enable_downloaded_marker" not in columns


def test_alembic_history_has_a_single_head():
    script = ScriptDirectory(str(SERVER_DIR / "alembic"))

    assert script.get_heads() == ["a7c41e9b2d10"]
