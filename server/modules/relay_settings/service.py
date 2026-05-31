import logging

from modules.relay.schemas import RelaySettingsUpdate as RelayLibtorrentUpdate
from modules.relay.service import RelayService
from modules.settings.schemas import RelaySettings, RelaySettingsUpdate
from modules.settings.service import SettingsService

logger = logging.getLogger(__name__)


class RelaySettingsService:
    def __init__(
        self,
        settings_service: SettingsService,
        relay_service: RelayService,
    ):
        self._settings_service = settings_service
        self._relay_service = relay_service

    def get_settings(self) -> RelaySettings:
        relay = self._settings_service.get_relay()
        if not relay:
            return RelaySettings()
        return relay

    def update_settings(self, payload: RelaySettingsUpdate) -> RelaySettings:
        # 1. Frissíti a beállítások megfelelő sorát az adatbázisban
        settings = self._settings_service.save_relay(payload)

        # 2. Konfigurálja a libtorrentet, hogy szinkronban legyen
        self.sync_settings()

        return settings

    def sync_settings(self) -> None:
        """Szinkronizálja az adatbázisban tárolt relay beállításokat a futó libtorrent session-nel."""
        settings = self.get_settings()
        if not settings:
            return

        libtorrent_update = RelayLibtorrentUpdate(
            download_limit=settings.download_limit,
            upload_limit=settings.upload_limit,
            port=settings.port,
            connections_limit=settings.connections_limit,
            torrent_connections_limit=settings.torrent_connections_limit,
            enable_upnp_and_natpmp=settings.enable_upnp_and_natpmp,
        )
        try:
            self._relay_service.update_settings(libtorrent_update)
            logger.info("⚙️ Libtorrent beállítások sikeresen szinkronizálva.")
        except Exception as e:
            logger.error(
                f"Hiba történt a libtorrent beállítások szinkronizálása során: {e}"
            )
