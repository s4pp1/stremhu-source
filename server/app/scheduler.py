from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.modules.indexers.background_tasks import run_indexers_cleanup
from app.modules.network.background_tasks import (
    run_check_ssl_certificate,
    run_network_ip_sync,
)
from app.modules.pairings.background_tasks import run_expired_pairings_cleanup
from app.modules.torrent_files.background_tasks import (
    run_torrent_files_retention_cleanup,
)


def setup_scheduler() -> AsyncIOScheduler:
    """Létrehozza az AsyncIOScheduler példányát és regisztrálja a modulok feladatait."""

    scheduler = AsyncIOScheduler()

    # Torrent fájlok cleaning feladat (naponta hajnali 3-kor)
    scheduler.add_job(
        run_torrent_files_retention_cleanup,
        trigger="cron",
        hour=3,
        minute=0,
        id="torrent_files_cleanup",
        replace_existing=True,
    )

    # Indexerek napi karbantartása (naponta hajnali 4-kor)
    scheduler.add_job(
        run_indexers_cleanup,
        trigger="cron",
        hour=4,
        minute=0,
        id="indexers_cleanup",
        replace_existing=True,
    )

    # Lejárt párosítások tisztítása (minden órában)
    scheduler.add_job(
        run_expired_pairings_cleanup,
        trigger="cron",
        hour="*",
        minute=0,
        id="expired_pairings_cleanup",
        replace_existing=True,
    )

    # DDNS IP szinkronizáció (5 percenként)
    scheduler.add_job(
        run_network_ip_sync,
        trigger="interval",
        minutes=5,
        id="ddns_ip_sync",
        replace_existing=True,
    )

    # SSL tanúsítvány ellenőrzése (naponta 5-kor)
    scheduler.add_job(
        run_check_ssl_certificate,
        trigger="cron",
        hour=5,
        minute=0,
        id="ssl_certificate_check",
        replace_existing=True,
    )

    return scheduler
