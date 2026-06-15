from app.common.database import db_session
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.schemas.internal import (
    RelaySettingsUpdate,
    SystemSettingsUpdate,
)


def ensure_default_settings():
    """Inicializálja vagy frissíti a rendszer- és relay-beállításokat alapértelmezett értékekkel minden indításkor."""
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)

            # System Settings inicializálása/frissítése
            settings_service.save_system(SystemSettingsUpdate())

            # Relay Settings inicializálása/frissítése
            settings_service.save_relay(RelaySettingsUpdate())
    except Exception as e:
        print(
            f"[HIBA] Nem sikerült inicializálni vagy frissíteni az alapértelmezett beállításokat: {e}"
        )
        raise
