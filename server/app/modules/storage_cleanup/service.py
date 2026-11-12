import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from shutil import disk_usage

from app.common.logger import logger
from app.config import config
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.relay.service import RelayService
from app.modules.settings.enums import (
    StorageCleanupThresholdUnitEnum,
    StorageCleanupTriggerEnum,
)
from app.modules.settings.schemas.internal import (
    StorageCleanupLastRun,
    SystemSettings,
)
from app.modules.settings.service import SettingsService
from app.modules.storage_cleanup.cache import (
    clear_hnr_pending_ids,
    get_hnr_pending_ids,
    set_hnr_pending_ids,
)
from app.modules.storage_cleanup.enums import StorageCleanupProtectedReasonEnum
from app.modules.storage_cleanup.schemas.api import (
    StorageCleanupQueueItem,
    StorageCleanupQueueResponse,
    StorageCleanupScoreComponent,
)
from app.modules.storage_cleanup.scoring import (
    COMPONENT_MAX_POINTS,
    GIB,
    ScoreBreakdown,
    TorrentMetrics,
    calculate_score,
    to_local_naive,
)
from app.modules.torrents.schemas.internal import TorrentWithLastPlayed
from app.modules.torrents.service import TorrentsService

# A libtorrent a fájlokat aszinkron módon törli, ezért adunk neki egy kis időt.
DELETE_SETTLE_SECONDS = 0.5

_PROTECTED_REASON_PRIORITY: dict[StorageCleanupProtectedReasonEnum, int] = {
    StorageCleanupProtectedReasonEnum.PINNED: 0,
    StorageCleanupProtectedReasonEnum.ACTIVE_STREAM: 1,
    StorageCleanupProtectedReasonEnum.HNR_PENDING: 2,
    StorageCleanupProtectedReasonEnum.HNR_UNKNOWN: 3,
    StorageCleanupProtectedReasonEnum.KEEP_SEED: 4,
}


@dataclass(frozen=True)
class _ScoredTorrent:
    torrent_id: str
    name: str
    breakdown: ScoreBreakdown
    downloaded_bytes: int
    protected_reason: StorageCleanupProtectedReasonEnum | None


class StorageCleanupService:
    def __init__(
        self,
        settings_service: SettingsService,
        indexer_accounts_service: IndexerAccountsService,
        indexer_definitions_service: IndexerDefinitionsService,
        torrents_service: TorrentsService,
        relay_service: RelayService,
    ):
        self._settings_service = settings_service
        self._indexer_accounts_service = indexer_accounts_service
        self._indexer_definitions_service = indexer_definitions_service
        self._torrents_service = torrents_service
        self._relay_service = relay_service

    def get_queue(self) -> StorageCleanupQueueResponse:
        settings = self._settings_service.find_system() or SystemSettings()
        return self._build_queue(settings)

    async def run(
        self,
        trigger: StorageCleanupTriggerEnum,
    ) -> StorageCleanupLastRun:
        settings = self._settings_service.find_system() or SystemSettings()
        summary = StorageCleanupLastRun(
            at=int(time.time()),
            trigger=trigger,
            free_before=0,
            free_after=0,
            deleted_count=0,
            threshold_reached=False,
        )

        # Az ütemezett futást kapcsolhatja ki a beállítás, a manuális futtatást nem.
        if (
            trigger is StorageCleanupTriggerEnum.SCHEDULED
            and not settings.storage_cleanup_enabled
        ):
            logger.info("ℹ️ A tárhely alapú takarítás ki van kapcsolva, kihagyva.")
            return summary

        try:
            free_bytes, total_bytes = self._measure()
            threshold_bytes = self._threshold_bytes(settings, total_bytes)

            summary.free_before = free_bytes
            summary.free_after = free_bytes
            summary.threshold_reached = free_bytes >= threshold_bytes

            if summary.threshold_reached:
                logger.info(
                    "✅ A szabad hely (%s) felette van a küszöbnek (%s), nincs törlés.",
                    free_bytes,
                    threshold_bytes,
                )
                return summary

            accounts = self._indexer_accounts_service.find_list()
            await self._refresh_hnr_cache(accounts, settings)

            queue = self._build_queue(
                settings,
                free_bytes=free_bytes,
                total_bytes=total_bytes,
                log_missing=True,
            )

            for item in queue.items:
                if summary.free_after >= queue.threshold_bytes:
                    break

                if item.score < queue.min_score:
                    break

                if item.protected_reason is not None:
                    continue

                # A futás közben induló stream ne veszítse el a torrentjét.
                if item.info_hash in self._active_info_hashes():
                    logger.info(
                        "⏭️ A(z) '%s' torrent közben aktív stream lett, kihagyva.",
                        item.name,
                    )
                    continue

                try:
                    self._torrents_service.delete(info_hash=item.info_hash)
                except Exception as e:
                    logger.exception(
                        "‼️ Nem sikerült törölni a(z) '%s' torrentet.", item.name
                    )
                    summary.error = str(e)
                    continue

                summary.deleted_count += 1
                logger.info(
                    "🗑️ Törölve: '%s' (%s), pontszám %s (%s).",
                    item.name,
                    item.downloaded_bytes,
                    item.score,
                    ", ".join(
                        f"{component.key.value}={component.points:.1f}"
                        for component in item.components
                    ),
                )

                await asyncio.sleep(DELETE_SETTLE_SECONDS)
                try:
                    summary.free_after = disk_usage(config.downloads_dir).free
                except OSError as e:
                    logger.warning("⚠️ Nem sikerült újramérni a szabad helyet: %s", e)

            summary.threshold_reached = summary.free_after >= queue.threshold_bytes
            if not summary.threshold_reached:
                logger.warning(
                    "⚠️ A takarítás után is a küszöb alatt van a szabad hely (%s < %s).",
                    summary.free_after,
                    queue.threshold_bytes,
                )
        except Exception as e:
            logger.exception("‼️ Hiba történt a tárhely alapú takarítás során.")
            summary.error = str(e)
        finally:
            self._save_last_run(summary)

        return summary

    def _measure(self) -> tuple[int, int]:
        usage = disk_usage(config.downloads_dir)
        return usage.free, usage.total

    def _save_last_run(self, summary: StorageCleanupLastRun) -> None:
        try:
            self._settings_service.update_system(
                storage_cleanup_last_run=summary,
            )
        except Exception:
            logger.exception("‼️ Nem sikerült elmenteni a tárhely takarítás eredményét.")

    async def _refresh_hnr_cache(
        self,
        accounts: list[IndexerAccountModel],
        settings: SystemSettings,
    ) -> None:
        async def refresh(account: IndexerAccountModel) -> None:
            if not self._hit_and_run_enabled(account, settings):
                set_hnr_pending_ids(account.indexer_id, [])
                return

            try:
                indexer_definition = self._indexer_definitions_service.get_by_id(
                    account.indexer_id
                )
                pending_ids = await indexer_definition.find_hit_and_run_ids()
            except Exception:
                # Elavult sikeres adat ne engedjen át egy időközben függővé vált torrentet.
                clear_hnr_pending_ids(account.indexer_id)
                logger.exception(
                    "‼️ Nem sikerült lekérni a(z) '%s' indexer Hit'n'Run listáját.",
                    account.indexer_id,
                )
                return

            set_hnr_pending_ids(account.indexer_id, pending_ids)

        await asyncio.gather(*(refresh(account) for account in accounts))

    def _build_queue(
        self,
        settings: SystemSettings,
        free_bytes: int | None = None,
        total_bytes: int | None = None,
        log_missing: bool = False,
    ) -> StorageCleanupQueueResponse:
        if free_bytes is None or total_bytes is None:
            free_bytes, total_bytes = self._measure()

        threshold_bytes = self._threshold_bytes(settings, total_bytes)

        accounts_by_id = {
            account.indexer_id: account
            for account in self._indexer_accounts_service.find_list()
        }
        relay_stats = self._relay_service.get_torrent_stats()
        active_hashes = self._active_info_hashes()
        now = datetime.now()

        grouped: dict[str, list[_ScoredTorrent]] = {}

        for row in self._torrents_service.get_torrents_with_last_played():
            info_hash = row.torrent.info_hash
            stats = relay_stats.get(info_hash)

            if stats is None:
                if log_missing:
                    logger.warning(
                        "⚠️ A(z) '%s' torrent nincs a relay munkamenetben, kihagyva.",
                        info_hash,
                    )
                continue

            breakdown = calculate_score(
                TorrentMetrics(
                    created_at=row.torrent.created_at,
                    last_played_at=row.last_played_at,
                    downloaded_bytes=stats.downloaded,
                    uploaded_bytes=stats.uploaded,
                    seeders=stats.seeders,
                    leechers=stats.leechers,
                    swarm_known=stats.swarm_known,
                ),
                now,
            )

            grouped.setdefault(info_hash, []).append(
                _ScoredTorrent(
                    torrent_id=row.torrent.torrent_id,
                    name=stats.name,
                    breakdown=breakdown,
                    downloaded_bytes=stats.downloaded,
                    protected_reason=self._protected_reason(
                        row,
                        active_hashes,
                        accounts_by_id,
                        settings,
                        now,
                    ),
                )
            )

        items: list[StorageCleanupQueueItem] = []

        for info_hash, rows in grouped.items():
            # A törlés minden azonos info_hash-ű sort elvisz, ezért a legszigorúbb
            # védelmi ok és a legmagasabb pontszám dönt a csoportról.
            best = max(
                rows,
                key=lambda row: (
                    row.breakdown.total,
                    row.downloaded_bytes,
                    row.torrent_id,
                ),
            )
            protected_reason = self._highest_priority_reason(rows)

            items.append(
                StorageCleanupQueueItem(
                    info_hash=info_hash,
                    name=best.name,
                    score=best.breakdown.total,
                    components=[
                        StorageCleanupScoreComponent(
                            key=key,
                            points=points,
                            max_points=COMPONENT_MAX_POINTS[key],
                        )
                        for key, points in best.breakdown.points().items()
                    ],
                    protected_reason=protected_reason,
                    would_delete=(
                        protected_reason is None
                        and best.breakdown.total >= settings.storage_cleanup_min_score
                    ),
                    downloaded_bytes=best.downloaded_bytes,
                )
            )

        items.sort(
            key=lambda item: (-item.score, -item.downloaded_bytes, item.info_hash)
        )

        return StorageCleanupQueueResponse(
            free_bytes=free_bytes,
            total_bytes=total_bytes,
            threshold_bytes=threshold_bytes,
            below_threshold=free_bytes < threshold_bytes,
            min_score=settings.storage_cleanup_min_score,
            hnr_known=all(
                item.protected_reason
                is not StorageCleanupProtectedReasonEnum.HNR_UNKNOWN
                for item in items
            ),
            items=items,
        )

    def _protected_reason(
        self,
        row: TorrentWithLastPlayed,
        active_hashes: set[str],
        accounts_by_id: dict[str, IndexerAccountModel],
        settings: SystemSettings,
        now: datetime,
    ) -> StorageCleanupProtectedReasonEnum | None:
        torrent = row.torrent

        if torrent.is_persisted:
            return StorageCleanupProtectedReasonEnum.PINNED

        if torrent.info_hash in active_hashes:
            return StorageCleanupProtectedReasonEnum.ACTIVE_STREAM

        account = accounts_by_id.get(torrent.indexer_id)

        if self._hit_and_run_enabled(account, settings):
            pending_ids = get_hnr_pending_ids(torrent.indexer_id)
            if pending_ids is None:
                return StorageCleanupProtectedReasonEnum.HNR_UNKNOWN
            if torrent.torrent_id in pending_ids:
                return StorageCleanupProtectedReasonEnum.HNR_PENDING

        keep_seed_seconds = self._keep_seed_seconds(account, settings)
        if keep_seed_seconds is not None:
            cutoff = now - timedelta(seconds=keep_seed_seconds)
            if to_local_naive(row.last_played_at) >= cutoff:
                return StorageCleanupProtectedReasonEnum.KEEP_SEED

        return None

    @staticmethod
    def _highest_priority_reason(
        rows: list[_ScoredTorrent],
    ) -> StorageCleanupProtectedReasonEnum | None:
        reasons = [
            row.protected_reason for row in rows if row.protected_reason is not None
        ]
        if not reasons:
            return None
        return min(reasons, key=lambda reason: _PROTECTED_REASON_PRIORITY[reason])

    def _active_info_hashes(self) -> set[str]:
        return {
            stream.torrent.info_hash
            for stream in self._relay_service.get_active_streams()
        }

    @staticmethod
    def _hit_and_run_enabled(
        account: IndexerAccountModel | None,
        settings: SystemSettings,
    ) -> bool:
        if account is not None and account.hit_and_run is not None:
            return account.hit_and_run
        return settings.hit_and_run

    @staticmethod
    def _keep_seed_seconds(
        account: IndexerAccountModel | None,
        settings: SystemSettings,
    ) -> int | None:
        keep_seed_seconds = (
            settings.keep_seed_seconds if settings.keep_seed_seconds > 0 else None
        )

        if account is not None and account.keep_seed_seconds is not None:
            keep_seed_seconds = account.keep_seed_seconds

        return keep_seed_seconds

    @staticmethod
    def _threshold_bytes(settings: SystemSettings, total_bytes: int) -> int:
        value = settings.storage_cleanup_threshold_value

        if (
            settings.storage_cleanup_threshold_unit
            == StorageCleanupThresholdUnitEnum.GB
        ):
            return value * GIB

        if value > 100:
            logger.warning(
                "⚠️ A tárhely küszöb %s%% nem lehet 100%% felett, 100%%-ra korlátozva.",
                value,
            )

        return int(total_bytes * max(0, min(100, value)) / 100)
