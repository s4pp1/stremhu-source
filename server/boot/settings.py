from server.common.database import db_session
from server.config import config
from server.modules.settings.dependencies import create_settings_service
from server.modules.settings.schemas.internal import (
    RelaySettingsUpdate,
    SystemSettingsUpdate,
)


def ensure_default_settings():
    """Inicializálja vagy frissíti a rendszer- és relay-beállításokat alapértelmezett értékekkel minden indításkor."""
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)

            # System Settings inicializálása/frissítése
            system_settings_payload = SystemSettingsUpdate()

            if config.downloads_dir:
                system_settings_payload.downloads_dir = config.downloads_dir

            settings_service.save_system(system_settings_payload)

            # Relay Settings inicializálása/frissítése
            settings_service.save_relay(RelaySettingsUpdate())
    except Exception as e:
        print(
            f"[HIBA] Nem sikerült inicializálni vagy frissíteni az alapértelmezett beállításokat: {e}"
        )
        raise
