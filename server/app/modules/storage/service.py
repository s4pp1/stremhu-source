import shutil
import threading

from app.common.logger import logger
from app.config import config
from app.modules.relay.schemas import RelayTorrentStorage
from app.modules.relay.service import RelayService
from app.modules.settings.schemas.internal import SystemSettings
from app.modules.settings.service import SettingsService
from app.modules.storage.schemas.internal import StorageModeEnum, StorageStatus
from app.modules.storage.utils import plan_eviction, reserve_bytes
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.service import TorrentsService

# Egyszerre csak egy helyfelszabadítás futhat (időzített + új letöltés).
_eviction_lock = threading.Lock()


class StorageService:
    def __init__(
        self,
        torrent_repository: TorrentRepository,
        torrents_service: TorrentsService,
        settings_service: SettingsService,
        relay_service: RelayService,
    ):
        self._torrent_repository = torrent_repository
        self._torrents_service = torrents_service
        self._settings_service = settings_service
        self._relay_service = relay_service

    def get_status(self) -> StorageStatus:
        system_settings = self._get_system_settings()
        usage = self._relay_service.get_storage_usage()
        status = self._calculate_status(system_settings, usage)

        usage_by_hash = {item.info_hash: item.downloaded for item in usage}
        evictable = self._torrent_repository.find_evictable()
        status.evictable_count = len(evictable)
        status.evictable_bytes = sum(
            usage_by_hash.get(torrent.info_hash, 0) for torrent in evictable
        )

        return status

    def ensure_free_space(
        self,
        extra_bytes: int = 0,
        protected_info_hashes: set[str] | None = None,
    ) -> list[str]:
        """Helyet szabadít fel a törölhetőként megjelölt torrentek törlésével.

        Csak akkor töröl, ha a "seed amíg nem kell a hely" mód be van kapcsolva,
        és a szabad hely kevesebb, mint a futó letöltések + `extra_bytes` +
        biztonsági tartalék. A legrégebben használt torrenttel kezd.
        """
        system_settings = self._get_system_settings()
        if not system_settings.seed_until_space_needed:
            return []

        protected = set(protected_info_hashes or set())

        with _eviction_lock:
            usage = self._relay_service.get_storage_usage()
            status = self._calculate_status(system_settings, usage)

            pending_bytes = sum(
                item.remaining_wanted
                for item in usage
                if item.info_hash not in protected
            )
            required_free = pending_bytes + max(0, extra_bytes) + status.reserve_bytes

            if status.free_bytes >= required_free:
                return []

            protected |= self._relay_service.get_active_info_hashes()
            usage_by_hash = {item.info_hash: item.downloaded for item in usage}

            candidates = [
                (torrent.info_hash, usage_by_hash.get(torrent.info_hash, 0))
                for torrent in self._torrent_repository.find_evictable()
                if torrent.info_hash not in protected
            ]

            to_delete = plan_eviction(
                free_bytes=status.free_bytes,
                required_free_bytes=required_free,
                candidates=candidates,
            )

            freed = 0
            for info_hash in to_delete:
                freed += usage_by_hash.get(info_hash, 0)
                self._torrents_service.delete(info_hash)
                logger.info("🧹 Helyfelszabadítás: torrent törölve (%s)", info_hash)

            if status.free_bytes + freed < required_free:
                logger.warning(
                    "⚠️ Nincs elég hely: szükséges %s bájt, elérhető %s bájt, "
                    "és nincs több törölhető torrent.",
                    required_free,
                    status.free_bytes + freed,
                )

            return to_delete

    def _get_system_settings(self) -> SystemSettings:
        return self._settings_service.find_system() or SystemSettings()

    def _calculate_status(
        self,
        system_settings: SystemSettings,
        usage: list[RelayTorrentStorage],
    ) -> StorageStatus:
        downloads_dir = config.downloads_dir
        downloads_dir.mkdir(parents=True, exist_ok=True)
        disk = shutil.disk_usage(downloads_dir)

        used_bytes = sum(item.downloaded for item in usage)
        pending_bytes = sum(item.remaining_wanted for item in usage)

        if system_settings.storage_limit_bytes:
            mode = StorageModeEnum.MANUAL
            capacity = system_settings.storage_limit_bytes
            # A kézi korlát sem lehet több, mint ami a lemezen ténylegesen szabad.
            free_bytes = max(0, min(capacity - used_bytes, disk.free))
        else:
            mode = StorageModeEnum.AUTO
            capacity = used_bytes + disk.free
            free_bytes = disk.free

        return StorageStatus(
            mode=mode,
            capacity_bytes=capacity,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            pending_bytes=pending_bytes,
            reserve_bytes=reserve_bytes(capacity),
            disk_total_bytes=disk.total,
            disk_free_bytes=disk.free,
            evictable_count=0,
            evictable_bytes=0,
        )
