import asyncio

from libtorrent_client.dependencies import get_libtorrent_client_service


async def alert_loop():
    """Háttérfolyamat, amely folyamatosan dolgozza fel a libtorrent figyelmeztetéseket (alerts).
    Másodpercenként kiolvassa a queue-t."""
    client = get_libtorrent_client_service()
    while True:
        try:
            client.process_alerts()
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)


async def resume_save_loop():
    """Háttérfolyamat, amely periódikusan mentést indit a torrent resume adatairól.
    10 percenként kikényszeríti a `.resume` fájlok felülírását."""
    client = get_libtorrent_client_service()
    while True:
        try:
            await asyncio.sleep(600)  # 10 perc
            client.trigger_save_resume_data()
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(60)
