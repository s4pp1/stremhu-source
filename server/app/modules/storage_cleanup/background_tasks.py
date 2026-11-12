from app.common.database import db_session
from app.common.logger import logger
from app.modules.settings.enums import StorageCleanupTriggerEnum
from app.modules.storage_cleanup.dependencies import create_storage_cleanup_service


async def run_storage_cleanup() -> None:
    """A tárhely alapú torrent takarítás ütemezett futtatása."""
    logger.info("⏰ Tárhely alapú torrent takarítás indítása...")
    try:
        with db_session() as db:
            service = create_storage_cleanup_service(db)
            summary = await service.run(StorageCleanupTriggerEnum.SCHEDULED)
        logger.info(
            "✅ Tárhely takarítás kész: törölve %s, szabad hely %s.",
            summary.deleted_count,
            summary.free_after,
        )
    except Exception:
        logger.exception("‼️ Hiba a tárhely takarítás során.")
