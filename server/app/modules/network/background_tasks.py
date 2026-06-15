from app.common.database import db_session
from app.common.logger import logger
from app.modules.network.dependencies import create_network_service


async def run_network_ip_sync() -> None:
    """DDNS IP szinkronizációs feladat (APScheduler-hez)."""
    logger.info("🔄 Kezdődik a DDNS IP szinkronizáció...")
    try:
        with db_session() as db:
            network_service = create_network_service(db)
            await network_service.sync_ip()
        logger.info("✅ A DDNS IP szinkronizáció befejeződött.")
    except Exception as e:
        logger.error(
            f"🚨 Hiba történt a DDNS IP szinkronizáció során: {e}",
            exc_info=e,
        )


async def run_check_ssl_certificate() -> None:
    """SSL tanúsítvány ellenőrzési feladat (APScheduler-hez)."""
    logger.info("🔄 Kezdődik az SSL tanúsítvány ellenőrzése...")
    try:
        with db_session() as db:
            network_service = create_network_service(db)
            await network_service.check_ssl_certificate()
        logger.info("✅ Az SSL tanúsítvány ellenőrzése befejeződött.")
    except Exception as e:
        logger.error(
            f"🚨 Hiba történt az SSL tanúsítvány ellenőrzése során: {e}",
            exc_info=e,
        )
