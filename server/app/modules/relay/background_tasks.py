import asyncio

from app.modules.relay.dependencies import get_relay_service


async def resume_save_loop():
    relay_service = get_relay_service()
    while True:
        try:
            await asyncio.sleep(600)
            relay_service.trigger_save_resume_data()
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(60)
