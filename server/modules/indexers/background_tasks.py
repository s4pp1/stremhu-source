from server.common.database import db_session
from server.common.logger import logger
from server.modules.indexers.dependencies import create_indexers_service


async def run_indexers_cleanup() -> None:
    """A bejelentkezett indexerek napi karbantartási feladatainak futtatása."""
    logger.info("🔄 Kezdődik a támogatott indexerek karbantartási takarítása...")
    try:
        with db_session() as db:
            indexers_service = create_indexers_service(db)
            await indexers_service.cleanup_torrents_by_rules()
        logger.info("✅ Az indexerek karbantartási takarítása befejeződött.")
    except Exception:
        logger.exception(
            "‼️ Hiba történt az indexerek karbantartási takarítása során.",
        )
