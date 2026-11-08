import asyncio
import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from apscheduler.events import EVENT_SCHEDULER_SHUTDOWN
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.common.async_utils import await_owned_task, owned_to_thread
from app.modules.indexers.background_tasks import run_indexers_cleanup
from app.modules.network.background_tasks import (
    run_check_ssl_certificate,
    run_network_ip_sync,
)
from app.modules.pairings.background_tasks import run_expired_pairings_cleanup
from app.modules.torrent_files.background_tasks import (
    run_torrent_files_retention_cleanup,
)

logger = logging.getLogger(__name__)


class ScheduledWorkError(RuntimeError):
    """A scheduler may log this message without exposing the original error."""


class ManagedScheduler(AsyncIOScheduler):
    def __init__(self, *args: Any, **kwargs: Any):
        self._closing = False
        self._owned_tasks: set[asyncio.Task[Any]] = set()
        self._close_task: asyncio.Task[None] | None = None
        super().__init__(*args, **kwargs)

    @property
    def active_jobs(self) -> int:
        return len(self._owned_tasks)

    def start(self, *args: Any, **kwargs: Any) -> None:
        if self._closing:
            raise RuntimeError("Scheduler is closed")
        super().start(*args, **kwargs)

    def stop_admission(self) -> None:
        self._closing = True
        if self.running:
            self.pause()

    def add_owned_job(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Job:
        if self._closing:
            raise RuntimeError("Scheduler is stopping")

        async def invoke(*job_args: Any, **job_kwargs: Any) -> Any:
            try:
                if inspect.iscoroutinefunction(function):
                    return await function(*job_args, **job_kwargs)
                return await owned_to_thread(function, *job_args, **job_kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                kind = type(error).__name__
                logger.error("Scheduled work failed: kind=%s", kind)
                raise ScheduledWorkError(f"Scheduled work failed ({kind})") from None

        @wraps(function)
        async def run(*job_args: Any, **job_kwargs: Any) -> Any:
            if self._closing:
                return None
            task = asyncio.create_task(invoke(*job_args, **job_kwargs), name="scheduled-work")
            self._owned_tasks.add(task)
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if not task.done():
                    task.cancel()
                try:
                    await await_owned_task(task)
                except asyncio.CancelledError:
                    pass
                if not self._closing:
                    raise
                logger.info("Scheduled work stopped")
                return None
            finally:
                self._owned_tasks.discard(task)

        return self.add_job(run, *args, **kwargs)

    async def _close_owned_jobs(self) -> None:
        tasks = tuple(self._owned_tasks)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if not self.running:
            return
        finished: asyncio.Future[None] = asyncio.get_running_loop().create_future()

        def shutdown_done(event: Any) -> None:
            if not finished.done():
                finished.set_result(None)

        self.add_listener(shutdown_done, EVENT_SCHEDULER_SHUTDOWN)
        try:
            # The pinned AsyncIOExecutor cannot honor wait=True for threads.
            # Owned work above is really finished before this public shutdown.
            self.shutdown(wait=False)
            await asyncio.wait_for(asyncio.shield(finished), timeout=5)
        finally:
            self.remove_listener(shutdown_done)

    async def aclose(self) -> None:
        if self._close_task is None:
            self.stop_admission()
            self._close_task = asyncio.create_task(self._close_owned_jobs(), name="scheduler-close")
        await await_owned_task(self._close_task)


def setup_scheduler() -> ManagedScheduler:
    """Létrehozza az AsyncIOScheduler példányát és regisztrálja a modulok feladatait."""

    scheduler = ManagedScheduler()

    # Torrent fájlok cleaning feladat (naponta hajnali 3-kor)
    scheduler.add_owned_job(
        run_torrent_files_retention_cleanup,
        trigger="cron",
        hour=3,
        minute=0,
        id="torrent_files_cleanup",
        replace_existing=True,
    )

    # Indexerek napi karbantartása (naponta hajnali 4-kor)
    scheduler.add_owned_job(
        run_indexers_cleanup,
        trigger="cron",
        hour=4,
        minute=0,
        id="indexers_cleanup",
        replace_existing=True,
    )

    # Lejárt párosítások tisztítása (minden órában)
    scheduler.add_owned_job(
        run_expired_pairings_cleanup,
        trigger="cron",
        hour="*",
        minute=0,
        id="expired_pairings_cleanup",
        replace_existing=True,
    )

    # DDNS IP szinkronizáció (5 percenként)
    scheduler.add_owned_job(
        run_network_ip_sync,
        trigger="interval",
        minutes=5,
        id="ddns_ip_sync",
        replace_existing=True,
    )

    # SSL tanúsítvány ellenőrzése (naponta 5-kor)
    scheduler.add_owned_job(
        run_check_ssl_certificate,
        trigger="cron",
        hour=5,
        minute=0,
        id="ssl_certificate_check",
        replace_existing=True,
    )

    return scheduler
