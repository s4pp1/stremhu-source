import asyncio

import httpx

from core.common.database import db_session
from core.common.logger import logger
from core.config import config
from core.modules.network.dependencies import create_network_service
from core.modules.settings.dependencies import create_settings_service
from core.modules.settings.enums import NetworkModeEnum


async def wait_for_port(port: int | None = None) -> bool:
    if port is None:
        try:
            with db_session() as db:
                settings_service = create_settings_service(db)
                port = settings_service.get_system().port
        except Exception:
            port = config.port

    start_time = asyncio.get_running_loop().time()
    while asyncio.get_running_loop().time() - start_time < 10.0:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            await asyncio.sleep(0.1)
    return False


async def verify_self_connection() -> None:
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)
            system_settings = settings_service.get_system()
            port = system_settings.port
            network_settings = settings_service.get_network()
            protocol = (
                "http" if network_settings.mode == NetworkModeEnum.MANUAL else "https"
            )
    except Exception:
        port = config.port
        protocol = "https"

    port_ready = await wait_for_port(port)
    if not port_ready:
        logger.warning(
            f"⚠️ Figyelmeztetés: A szerver portja ({port}) nem nyílt meg a megadott időn belül!"
        )
        return

    host = f"{protocol}://{config.host_ip}:{port}"
    url = f"{host}/api/health"

    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            await client.get(url)
            logger.info("✅ Sikeres ön-ellenőrzés! A szerver elérhető.")

    except Exception:
        logger.warning(
            f"⚠️  Az ön-ellenőrzés sikertelen ({host}). Nem biztos, hogy jó a HOST_IP beállítás."
        )


async def run_network_ip_sync() -> None:
    logger.info("🔄 Kezdődik a DDNS IP szinkronizáció...")
    try:
        with db_session() as db:
            network_service = create_network_service(db)
            await network_service.sync_ip()
        logger.info("✅ A DDNS IP szinkronizáció befejeződött.")
    except Exception:
        logger.exception("‼️ Hiba történt a DDNS IP szinkronizáció során.")


async def run_check_ssl_certificate() -> None:
    logger.info("🔄 Kezdődik az SSL tanúsítvány ellenőrzése...")
    try:
        with db_session() as db:
            network_service = create_network_service(db)
            await network_service.check_ssl_certificate()
        logger.info("✅ Az SSL tanúsítvány ellenőrzése befejeződött.")
    except Exception as e:
        logger.error(
            f"‼️ Hiba történt az SSL tanúsítvány ellenőrzése során: {e}",
            exc_info=e,
        )
