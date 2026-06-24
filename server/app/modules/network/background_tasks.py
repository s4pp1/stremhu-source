import asyncio
import os
import signal

import httpx

from app.common.database import db_session
from app.common.logger import logger
from app.config import config
from app.modules.network.dependencies import create_network_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.enums import NetworkModeEnum


async def wait_for_port() -> bool:
    start_time = asyncio.get_running_loop().time()
    while asyncio.get_running_loop().time() - start_time < 10.0:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", config.port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            await asyncio.sleep(0.1)
    return False


async def verify_self_connection() -> None:
    port_ready = await wait_for_port()
    if not port_ready:
        logger.error(
            f"🚨 Kritikus hiba: A szerver portja ({config.port}) nem nyílt meg a megadott időn belül!"
        )
        os.kill(os.getpid(), signal.SIGTERM)
        return

    try:
        with db_session() as db:
            settings_service = create_settings_service(db)
            network_settings = settings_service.get_network()
            protocol = (
                "http" if network_settings.mode == NetworkModeEnum.MANUAL else "https"
            )
    except Exception:
        protocol = "https"

    host = f"{protocol}://{config.host_ip}:{config.port}"
    url = f"{host}/api/health"

    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            await client.get(url)
            logger.info("✅ Sikeres ön-ellenőrzés! A szerver elérhető.")
            return

    except Exception:
        logger.error(
            f"🚨 Kritikus hiba: Nem sikerült csatlakozni a szerverhez a megadott címen ({host}). Kérlek ellenőrizd a HOST_IP beállítást, hogy biztosan a szerver IP-je legyen megadva!"
        )

    logger.error("🛑 Az ön-ellenőrzés sikertelen. Az alkalmazás leállítása...")
    os.kill(os.getpid(), signal.SIGTERM)


async def run_network_ip_sync() -> None:
    logger.info("🔄 Kezdődik a DDNS IP szinkronizáció...")
    try:
        with db_session() as db:
            network_service = create_network_service(db)
            await network_service.sync_ip()
        logger.info("✅ A DDNS IP szinkronizáció befejeződött.")
    except Exception:
        logger.exception("🚨 Hiba történt a DDNS IP szinkronizáció során.")


async def run_check_ssl_certificate() -> None:
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
