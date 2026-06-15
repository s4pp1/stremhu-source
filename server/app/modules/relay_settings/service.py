from app.common.logger import logger
from app.modules.relay.schemas import RelaySettingsUpdate as RelayLibtorrentUpdate
from app.modules.relay.service import RelayService
from app.modules.settings.schemas.internal import RelaySettings, RelaySettingsUpdate
from app.modules.settings.service import SettingsService


class RelaySettingsService:
    def __init__(
        self,
        settings_service: SettingsService,
        relay_service: RelayService,
    ):
        self._settings_service = settings_service
        self._relay_service = relay_service

    def get_settings(self) -> RelaySettings:
        return self._settings_service.get_relay()

    def update_settings(self, payload: RelaySettingsUpdate) -> RelaySettings:
        settings = self._settings_service.save_relay(payload)
        self.sync_settings()

        return settings

    def sync_settings(self) -> None:
        """Szinkronizálja az adatbázisban tárolt relay beállításokat a futó libtorrent session-nel."""
        settings = self.get_settings()

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
        except Exception:
            logger.exception(
                "❌ Hiba történt a Relay beállítások szinkronizálása során."
            )
