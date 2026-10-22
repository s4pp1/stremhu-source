from server.common.database import db_session
from server.common.logger import logger
from server.modules.pairings.repository import PairingsRepository
from server.modules.pairings.service import PairingsService


def run_expired_pairings_cleanup():
    """Tisztító feladat az elavult eszközpárosítási kódokhoz (APScheduler-hez)."""
    logger.info(
        "⏰ Automatikus lejárt párosítások tisztítása indítása (APScheduler)..."
    )

    try:
        with db_session() as db:
            repository = PairingsRepository(db)
            service = PairingsService(repository)
            service.cleanup_expired_pairings()
        logger.info(
            "✅ Automatikus lejárt párosítások tisztítása sikeresen befejeződött."
        )
    except Exception as e:
        logger.error(
            f"❌ Hiba történt az automatikus párosítások tisztítása közben: {e}"
        )
