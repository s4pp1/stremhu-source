import asyncio

from app.common.database import db_session
from app.common.logger import logger
from app.modules.indexers.dependencies import create_indexers_service
from app.modules.storage.background_tasks import run_storage_check


async def run_indexers_cleanup() -> None:
    """A bejelentkezett indexerek napi karbantartási feladatainak futtatása."""
    logger.info("🔄 Kezdődik a támogatott indexerek karbantartási takarítása...")
    try:
        with db_session() as db:
            indexers_service = create_indexers_service(db)
            await indexers_service.cleanup_torrents_by_rules()
        logger.info("✅ Az indexerek karbantartási takarítása befejeződött.")
        # A friss jelölések alapján azonnal ellenőrizzük a szabad helyet.
        await asyncio.to_thread(run_storage_check)
    except Exception:
        logger.exception(
            "‼️ Hiba történt az indexerek karbantartási takarítása során.",
        )
