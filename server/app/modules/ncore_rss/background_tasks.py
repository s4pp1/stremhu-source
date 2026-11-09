from app.common.database import db_session
from app.common.logger import logger
from app.modules.ncore_rss.dependencies import create_ncore_rss_service


async def run_ncore_rss_sync() -> None:
    """Poll the configured nCore feed; an unconfigured feed is a no-op."""
    try:
        with db_session() as db:
            service = create_ncore_rss_service(db)
            status = service.get_status()
            if not status.configured or not status.ncore_connected:
                return
            await service.sync()
    except Exception:
        logger.exception("Nem sikerült frissíteni az nCore RSS feedet.")
