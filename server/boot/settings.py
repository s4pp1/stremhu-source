from common.database import db_session
from modules.settings.dependencies import create_settings_service
from modules.settings.schemas import RelaySettingsUpdate, SystemSettingsSave


def ensure_default_settings():
    """Inicializálja vagy frissíti a rendszer- és relay-beállításokat alapértelmezett értékekkel minden indításkor."""
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)

            # System Settings inicializálása/frissítése
            settings_service.save_system(SystemSettingsSave())

            # Relay Settings inicializálása/frissítése
            settings_service.save_relay(RelaySettingsUpdate())
    except Exception as e:
        print(
            f"[HIBA] Nem sikerült inicializálni vagy frissíteni az alapértelmezett beállításokat: {e}"
        )
        raise
