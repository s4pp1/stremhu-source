import asyncio
from common.logger import logger
import os
import sys

class SystemService:
    async def restart(self):
        """Ütemezi a szerverfolyamat automatikus újraindítását."""
        logger.info("⏱️ Szerver újraindítás ütemezve 2 másodperc múlva...")
        await asyncio.sleep(2)
        try:
            logger.info("🚀 Szerver újraindítása folyamatban...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.critical(
                "Súlyos hiba történt az automatikus újraindítás során: %s", e
            )
