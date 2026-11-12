import asyncio
import datetime
from collections import namedtuple
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.common.database import Base, connect_args
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.playback_histories.models import PlaybackHistoryModel
from app.modules.relay.schemas import RelayTorrentStats
from app.modules.relay.service import RelayService
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.enums import (
    SettingsKeyEnum,
    StorageCleanupThresholdUnitEnum,
    StorageCleanupTriggerEnum,
)
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.schemas.internal import SystemSettingsUpdate
from app.modules.settings.service import SettingsService
from app.modules.storage_cleanup import (
    cache as storage_cleanup_cache,
    service as storage_cleanup_service,
)
from app.modules.storage_cleanup.cache import set_hnr_pending_ids
from app.modules.storage_cleanup.enums import StorageCleanupProtectedReasonEnum
from app.modules.storage_cleanup.service import StorageCleanupService
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentWithLastPlayed
from app.modules.torrents.service import TorrentsService

GIB = 1024**3
TOTAL_BYTES = 100 * GIB

DiskUsage = namedtuple("DiskUsage", "total used free")


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/app.db", connect_args=connect_args)
    Base.metadata.create_all(engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_hnr_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(storage_cleanup_cache, "_hnr_pending_ids", {})


class FakeRelayService:
    def __init__(self, free_bytes: int):
        self.state = {"total": TOTAL_BYTES, "free": free_bytes}
        self.stats: dict[str, RelayTorrentStats] = {}
        self.active: set[str] = set()
        self.deleted: list[str] = []

    def add(
        self,
        info_hash: str,
        downloaded: int,
        *,
        seeders: int = 10,
        leechers: int = 0,
        uploaded: int = 0,
        swarm_known: bool = True,
    ) -> None:
        self.stats[info_hash] = RelayTorrentStats(
            name=f"name-{info_hash}",
            downloaded=downloaded,
            uploaded=uploaded,
            seeders=seeders,
            leechers=leechers,
            swarm_known=swarm_known,
        )

    def get_torrent_stats(self) -> dict[str, RelayTorrentStats]:
        return dict(self.stats)

    def get_active_streams(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(torrent=SimpleNamespace(info_hash=info_hash))
            for info_hash in self.active
        ]

    def delete_torrent(self, info_hash: str) -> None:
        self.deleted.append(info_hash)
        removed = self.stats.pop(info_hash, None)
        if removed is not None:
            self.state["free"] += removed.downloaded


class FakeIndexerDefinition:
    def __init__(
        self, pending_ids: list[str] | None = None, error: Exception | None = None
    ):
        self._pending_ids = pending_ids or []
        self._error = error

    async def find_hit_and_run_ids(self) -> list[str]:
        if self._error is not None:
            raise self._error
        return list(self._pending_ids)


class FakeIndexerDefinitionsService:
    def __init__(self, definitions: dict[str, FakeIndexerDefinition] | None = None):
        self._definitions = definitions or {}

    def get_by_id(self, indexer_id: str) -> FakeIndexerDefinition:
        return self._definitions[indexer_id]


class FakeTorrentsService:
    def __init__(self, repository: TorrentRepository, relay: FakeRelayService):
        self._repository = repository
        self._relay = relay

    def get_torrents_with_last_played(self) -> list[TorrentWithLastPlayed]:
        return self._repository.find_with_last_played()

    def delete(self, info_hash: str) -> None:
        self._repository.delete(info_hash=info_hash)
        self._relay.delete_torrent(info_hash)


def seed_indexer(
    db: Session,
    indexer_id: str,
    *,
    hit_and_run: bool | None,
    keep_seed_seconds: int | None = None,
) -> None:
    db.add(
        IndexerDefinitionModel(
            id=indexer_id,
            name=indexer_id.upper(),
            url="http://localhost",
            details_path="/details/{torrent_id}",
        )
    )
    db.add(
        IndexerAccountModel(
            indexer_id=indexer_id,
            username="u",
            password="p",
            hit_and_run=hit_and_run,
            keep_seed_seconds=keep_seed_seconds,
        )
    )


def seed_torrent(
    db: Session,
    info_hash: str,
    indexer_id: str,
    torrent_id: str,
    *,
    created_days: float,
    played_days: float | None,
    pinned: bool = False,
) -> None:
    now = datetime.datetime.now()
    db.execute(
        text(
            "INSERT INTO torrent_files (indexer_id, torrent_id, info_hash,"
            " torrent_bytes, last_used_at, created_at)"
            " VALUES (:indexer_id, :torrent_id, :info_hash, X'00', :now, :now)"
        ),
        {
            "indexer_id": indexer_id,
            "torrent_id": torrent_id,
            "info_hash": info_hash,
            "now": now.isoformat(sep=" "),
        },
    )
    db.add(
        TorrentModel(
            info_hash=info_hash,
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            is_persisted=pinned,
            created_at=now - datetime.timedelta(days=created_days),
        )
    )
    db.add(
        PlaybackHistoryModel(
            playback_id=f"playback-{indexer_id}-{torrent_id}",
            user_id="user-1",
            indexer_id=indexer_id,
            torrent_id=torrent_id,
            file_index=0,
            torrent_name=f"name-{info_hash}",
            file_name="file.mkv",
            imdb_info=None,
            client=None,
            created_at=now - datetime.timedelta(days=played_days or 0),
        )
    )


def save_settings(db: Session, **overrides: object) -> None:
    values: dict[str, object] = {
        "hit_and_run": False,
        "keep_seed_seconds": 0,
        "storage_cleanup_enabled": True,
        "storage_cleanup_threshold_value": 30,
        "storage_cleanup_threshold_unit": StorageCleanupThresholdUnitEnum.PERCENT,
        "storage_cleanup_min_score": 0,
    }
    values.update(overrides)
    create_settings_service(db).save_system(
        SystemSettingsUpdate(**values)  # pyright: ignore[reportArgumentType]
    )


def build_cleanup_service(
    db: Session,
    relay: FakeRelayService,
    definitions: FakeIndexerDefinitionsService | None = None,
) -> StorageCleanupService:
    return StorageCleanupService(
        settings_service=create_settings_service(db),
        indexer_accounts_service=create_indexer_accounts_service(db),
        indexer_definitions_service=cast(
            IndexerDefinitionsService, definitions or FakeIndexerDefinitionsService()
        ),
        torrents_service=cast(
            TorrentsService, FakeTorrentsService(TorrentRepository(db), relay)
        ),
        relay_service=cast(RelayService, relay),
    )


def patch_disk(monkeypatch: pytest.MonkeyPatch, relay: FakeRelayService) -> None:
    monkeypatch.setattr(
        storage_cleanup_service,
        "disk_usage",
        lambda _: DiskUsage(
            total=relay.state["total"],
            used=relay.state["total"] - relay.state["free"],
            free=relay.state["free"],
        ),
    )
    monkeypatch.setattr(storage_cleanup_service, "DELETE_SETTLE_SECONDS", 0)


def read_torrent_hashes(session_factory: sessionmaker[Session]) -> set[str]:
    with session_factory() as db:
        return {hash_ for (hash_,) in db.query(TorrentModel.info_hash).all()}


def test_queue_marks_reasons_and_order(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "hnr", hit_and_run=True, keep_seed_seconds=7 * 86400)
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(
            db,
            "hash-pinned",
            "free",
            "t1",
            created_days=200,
            played_days=200,
            pinned=True,
        )
        seed_torrent(db, "hash-active", "free", "t2", created_days=200, played_days=200)
        seed_torrent(db, "hash-hnr", "hnr", "t-hnr", created_days=200, played_days=200)
        seed_torrent(db, "hash-keep", "hnr", "t-keep", created_days=200, played_days=1)
        seed_torrent(db, "hash-free", "free", "t3", created_days=100, played_days=100)
        seed_torrent(db, "hash-low", "free", "t4", created_days=0, played_days=0)
        save_settings(db, storage_cleanup_min_score=60)
        db.commit()

    set_hnr_pending_ids("hnr", ["t-hnr"])

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.active.add("hash-active")
    for info_hash, size in [
        ("hash-pinned", 10 * GIB),
        ("hash-active", 10 * GIB),
        ("hash-hnr", 10 * GIB),
        ("hash-keep", 10 * GIB),
        ("hash-free", 10 * GIB),
        ("hash-low", 0),
    ]:
        relay.add(
            info_hash,
            size,
            seeders=10 if info_hash != "hash-low" else 0,
            leechers=0 if info_hash != "hash-low" else 20,
            uploaded=0 if info_hash != "hash-low" else 5 * GIB,
        )
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        queue = build_cleanup_service(db, relay).get_queue()

    reasons = {item.info_hash: item.protected_reason for item in queue.items}

    assert len(queue.items) == 6
    assert reasons["hash-pinned"] is StorageCleanupProtectedReasonEnum.PINNED
    assert reasons["hash-active"] is StorageCleanupProtectedReasonEnum.ACTIVE_STREAM
    assert reasons["hash-hnr"] is StorageCleanupProtectedReasonEnum.HNR_PENDING
    assert reasons["hash-keep"] is StorageCleanupProtectedReasonEnum.KEEP_SEED
    assert reasons["hash-free"] is None
    assert reasons["hash-low"] is None

    deletable = {item.info_hash for item in queue.items if item.would_delete}
    assert deletable == {"hash-free"}

    scores = [item.score for item in queue.items]
    assert scores == sorted(scores, reverse=True)

    order = [item.info_hash for item in queue.items]
    assert order.index("hash-free") < order.index("hash-low")
    assert queue.hnr_known is True
    assert queue.below_threshold is True
    assert queue.threshold_bytes == int(TOTAL_BYTES * 30 / 100)


def test_queue_hnr_unknown_after_start(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "hnr", hit_and_run=True)
        seed_torrent(db, "hash-a", "hnr", "t1", created_days=200, played_days=200)
        save_settings(db)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-a", 10 * GIB)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        queue = build_cleanup_service(db, relay).get_queue()

    assert len(queue.items) == 1
    assert (
        queue.items[0].protected_reason is StorageCleanupProtectedReasonEnum.HNR_UNKNOWN
    )
    assert queue.items[0].would_delete is False
    assert queue.hnr_known is False


def test_run_deletes_until_threshold_in_score_order(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-a", "free", "t1", created_days=60, played_days=60)
        seed_torrent(db, "hash-b", "free", "t2", created_days=20, played_days=20)
        seed_torrent(
            db,
            "hash-pinned",
            "free",
            "t3",
            created_days=200,
            played_days=200,
            pinned=True,
        )
        save_settings(db)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-a", 20 * GIB, seeders=50, leechers=0, uploaded=0)
    relay.add("hash-b", 15 * GIB, seeders=50, leechers=0, uploaded=0)
    relay.add("hash-pinned", 50 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        service = build_cleanup_service(db, relay)
        summary = asyncio.run(service.run(StorageCleanupTriggerEnum.MANUAL))
        db.commit()

    assert relay.deleted == ["hash-a", "hash-b"]
    assert summary.deleted_count == 2
    assert summary.threshold_reached is True
    assert summary.free_after == 36 * GIB
    assert summary.trigger is StorageCleanupTriggerEnum.MANUAL
    assert read_torrent_hashes(session_factory) == {"hash-pinned"}


def test_run_respects_min_score(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-a", "free", "t1", created_days=60, played_days=60)
        save_settings(db, storage_cleanup_min_score=100)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-a", 20 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        summary = asyncio.run(
            build_cleanup_service(db, relay).run(StorageCleanupTriggerEnum.MANUAL)
        )

    assert relay.deleted == []
    assert summary.deleted_count == 0
    assert summary.threshold_reached is False


def test_run_hnr_fetch_failure_skips_indexer(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "hnr", hit_and_run=True)
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-hnr", "hnr", "t1", created_days=200, played_days=200)
        seed_torrent(db, "hash-free", "free", "t2", created_days=200, played_days=200)
        save_settings(db)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-hnr", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    relay.add("hash-free", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    definitions = FakeIndexerDefinitionsService(
        {
            "hnr": FakeIndexerDefinition(error=RuntimeError("boom")),
            "free": FakeIndexerDefinition(),
        }
    )

    with session_factory() as db:
        summary = asyncio.run(
            build_cleanup_service(db, relay, definitions).run(
                StorageCleanupTriggerEnum.MANUAL
            )
        )
        db.commit()

    assert relay.deleted == ["hash-free"]
    assert summary.deleted_count == 1
    assert read_torrent_hashes(session_factory) == {"hash-hnr"}


def test_scheduled_disabled_does_nothing(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-a", "free", "t1", created_days=200, played_days=200)
        save_settings(db, storage_cleanup_enabled=False)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-a", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        summary = asyncio.run(
            build_cleanup_service(db, relay).run(StorageCleanupTriggerEnum.SCHEDULED)
        )
        db.commit()

        assert summary.deleted_count == 0
        settings = create_settings_service(db).find_system()
        assert settings is not None
        assert settings.storage_cleanup_last_run is None

    assert relay.deleted == []
    assert read_torrent_hashes(session_factory) == {"hash-a"}


def test_manual_works_when_disabled(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-a", "free", "t1", created_days=200, played_days=200)
        save_settings(db, storage_cleanup_enabled=False)
        db.commit()

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-a", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        summary = asyncio.run(
            build_cleanup_service(db, relay).run(StorageCleanupTriggerEnum.MANUAL)
        )
        db.commit()

        settings = create_settings_service(db).find_system()
        assert settings is not None
        last_run = settings.storage_cleanup_last_run

    assert relay.deleted == ["hash-a"]
    assert summary.deleted_count == 1
    assert last_run is not None
    assert last_run.trigger is StorageCleanupTriggerEnum.MANUAL
    assert last_run.deleted_count == 1


def test_run_above_threshold_persists_summary_without_deleting(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-a", "free", "t1", created_days=200, played_days=200)
        save_settings(db, storage_cleanup_threshold_value=10)
        db.commit()

    relay = FakeRelayService(free_bytes=90 * GIB)
    relay.add("hash-a", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        summary = asyncio.run(
            build_cleanup_service(db, relay).run(StorageCleanupTriggerEnum.SCHEDULED)
        )
        db.commit()

        settings = create_settings_service(db).find_system()
        assert settings is not None
        last_run = settings.storage_cleanup_last_run

    assert relay.deleted == []
    assert summary.deleted_count == 0
    assert summary.threshold_reached is True
    assert last_run is not None
    assert last_run.threshold_reached is True
    assert last_run.free_before == 90 * GIB


def test_duplicate_info_hash_group_is_protected_by_any_row(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        seed_indexer(db, "hnr", hit_and_run=True)
        seed_indexer(db, "free", hit_and_run=False)
        seed_torrent(db, "hash-dup", "hnr", "t-hnr", created_days=200, played_days=200)
        seed_torrent(
            db, "hash-dup", "free", "t-free", created_days=200, played_days=200
        )
        save_settings(db)
        db.commit()

    set_hnr_pending_ids("hnr", ["t-hnr"])

    relay = FakeRelayService(free_bytes=1 * GIB)
    relay.add("hash-dup", 40 * GIB, seeders=50, leechers=0, uploaded=0)
    patch_disk(monkeypatch, relay)

    with session_factory() as db:
        service = build_cleanup_service(db, relay)
        queue = service.get_queue()
        summary = asyncio.run(service.run(StorageCleanupTriggerEnum.MANUAL))
        db.commit()

    assert len(queue.items) == 1
    assert (
        queue.items[0].protected_reason is StorageCleanupProtectedReasonEnum.HNR_PENDING
    )
    assert queue.items[0].would_delete is False
    assert relay.deleted == []
    assert summary.deleted_count == 0
    assert read_torrent_hashes(session_factory) == {"hash-dup"}


def test_old_settings_json_gets_defaults(session_factory: sessionmaker[Session]):
    with session_factory() as db:
        SettingsRepository(db).save(
            SettingsKeyEnum.SYSTEM,
            {
                "hit_and_run": True,
                "keep_seed_seconds": 0,
                "cache_retention_seconds": 1209600,
            },
        )
        db.commit()

    with session_factory() as db:
        settings = SettingsService(SettingsRepository(db)).find_system()

    assert settings is not None
    assert settings.storage_cleanup_enabled is False
    assert settings.storage_cleanup_threshold_value == 10
    assert settings.storage_cleanup_threshold_unit is (
        StorageCleanupThresholdUnitEnum.PERCENT
    )
    assert settings.storage_cleanup_min_score == 60
    assert settings.storage_cleanup_last_run is None
