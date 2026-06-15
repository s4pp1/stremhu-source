from app.common.database import db_session
from app.common.logger import logger
from app.modules.torrent_files.dependencies import create_torrent_files_service


def run_torrent_files_retention_cleanup():
    """Tisztító feladat az elavult és inaktív torrent gyorsítótár rekordokhoz (APScheduler-hez)."""
    logger.info(
        "⏰ Automatikus gyorsítótár (torrent_files) tisztítás indítása (APScheduler)..."
    )

    try:
        with db_session() as db:
            torrent_files_service = create_torrent_files_service(db)
            torrent_files_service.run_retention_cleanup()
        logger.info("✅ Automatikus gyorsítótár tisztítás sikeresen befejeződött.")
    except Exception as e:
        logger.error(
            f"❌ Hiba történt az automatikus gyorsítótár tisztítás közben: {e}"
        )
