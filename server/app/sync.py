from fastapi import FastAPI

from app.common.database import db_session
from app.common.logger import logger
from app.modules.indexer_definitions.dependencies import (
    get_indexer_definitions_service,
)
from app.modules.media_attributes.dependencies import create_media_attributes_service
from app.modules.preferences.dependencies import create_preferences_service
from app.modules.relay_settings.dependencies import create_relay_settings_service
from app.modules.roles.dependencies import create_roles_service


def sync_database_and_settings(app: FastAPI) -> None:
    try:
        with db_session() as db:
            # 1. Szerepkörök szinkronizálása (elsőként, mert a felhasználók hivatkoznak rájuk)
            roles_service = create_roles_service(db)
            roles_service.sync_to_db()

            # 2. Preferenciák szinkronizálása (az attribútumok hivatkoznak rájuk)
            preferences_service = create_preferences_service(db)
            preferences_service.sync_to_db()

            # 3. Attribútumok szinkronizálása
            media_attributes_service = create_media_attributes_service(db)
            media_attributes_service.sync_to_db()

            # 4. Indexer definíciók szinkronizálása
            indexer_definitions_service = get_indexer_definitions_service()
            indexer_definitions_service.sync_to_db(db)

            # 5. Libtorrent beállítások szinkronizálása a SettingsService és a RelayService között
            relay_settings_service = create_relay_settings_service(db)
            relay_settings_service.sync_settings()

        logger.info("✅ Rendszerindításkori szinkronizációk sikeresen lefutottak.")
    except Exception:
        logger.exception("❌ Hiba történt a szinkronizáció alatt!")
