import asyncio
import os
import sys

from common.logger import logger


class SystemService:
    async def restart(self):
        await asyncio.sleep(2)
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.critical(
                "Súlyos hiba történt az automatikus újraindítás során: %s", e
            )
