import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pydash
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from setproctitle import setproctitle
from starlette.middleware.sessions import SessionMiddleware

from app.api import api_router
from app.common.async_utils import (
    await_owned_task,
    drain_background_tasks,
    owned_to_thread,
)
from app.common.lifecycle import StoppingPolicy
from app.common.logger import logger
from app.common.sensitive_responses import SensitiveResponsePolicy
from app.common.session_origin import clear_origin_cache
from app.common.spa_static_files import SPAStaticFiles
from app.config import NodeEnv, config
from app.exceptions import setup_exception_handlers
from app.modules.auth.bootstrap import initialize_bootstrap_state
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.indexers.search import (
    close_indexer_cache_refresh,
    open_indexer_cache_refresh,
)
from app.modules.indexers.service import invalidate_indexer_cache
from app.modules.media_attributes.tech_info_cache import (
    close_tech_info_prefetch,
    open_tech_info_prefetch,
)
from app.modules.network.background_tasks import verify_self_connection
from app.modules.network.service import close_network_setup
from app.modules.relay.background_tasks import resume_save_loop
from app.modules.relay.dependencies import get_relay_service
from app.modules.relay.service import ResumeSaveResult
from app.modules.stream.active_playback import clear_active_playbacks
from app.modules.stream.service import clear_playback_history_state
from app.modules.stremio.service import (
    close_stream_searches,
    invalidate_stream_cache,
    open_stream_searches,
)
from app.modules.stremio.tvdb_resolver import tvdb_resolver
from app.modules.torrent_source_provider.service import (
    close_source_searches,
    open_source_searches,
)
from app.modules.torrents.background_tasks import (
    register_persisted_torrents_callbacks,
    restore_torrents,
)
from app.modules.torrents.resume_writer import ResumeWriter
from app.scheduler import setup_scheduler
from app.sync import sync_database_and_settings

setproctitle("stremhu-source")


async def _cancel_producers(tasks: list[asyncio.Task[Any]]) -> bool:
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [result for result in results if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError)]
        for error in failures:
            logger.error("Producer stopped with error: kind=%s", type(error).__name__)
        return not failures
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stopping = True
    definitions = relay = writer = scheduler = None
    unregister_resume = None
    producers: list[asyncio.Task[Any]] = []
    try:
        open_stream_searches()
        open_source_searches()
        open_tech_info_prefetch()
        open_indexer_cache_refresh()
        if config.node_env == NodeEnv.DEV:
            config.openapi_dir.mkdir(parents=True, exist_ok=True)
            with (config.openapi_dir / "openapi.json").open("w", encoding="utf-8") as output:
                json.dump(app.openapi(), output, indent=2, ensure_ascii=False)

        # Acquire lifecycle ownership before startup operations can fail.
        definitions = get_indexer_definitions_service()
        relay = get_relay_service()
        sync_database_and_settings(app)
        await owned_to_thread(initialize_bootstrap_state)
        clear_origin_cache()
        writer = ResumeWriter()
        writer.start()
        unregister_resume = register_persisted_torrents_callbacks(writer)
        restore_torrents()
        producers.append(asyncio.create_task(resume_save_loop(), name="resume-producer"))
        producers.append(asyncio.create_task(relay.priority_manager_loop(), name="relay-priority"))
        scheduler = setup_scheduler()
        scheduler.start()
        if not config.reverse_proxy_domain:
            producers.append(asyncio.create_task(verify_self_connection(), name="self-connection"))
        app.state.stopping = False
        yield
    finally:
        # Hypercorn normally drains HTTP first. This guard also covers startup
        # failure and repeated in-process lifespans without recreating clients.
        app.state.stopping = True
        report: dict[str, Any] = {"complete": True, "failed_stages": [], "overdue": False}
        app.state.shutdown_result = report

        async def step(name: str, work: Callable[[], Awaitable[Any]]) -> None:
            try:
                result = await work()
                if isinstance(result, ResumeSaveResult):
                    report["final_resume"] = {
                        "requested": result.requested, "accepted": result.accepted,
                        "failed": result.failed, "timed_out": result.timed_out,
                    }
                    if not result.complete:
                        logger.warning(
                            "Final resume partial: requested=%s accepted=%s failed=%s timed_out=%s",
                            result.requested, result.accepted, result.failed, result.timed_out,
                        )
                if result is False or getattr(result, "complete", True) is False:
                    report["complete"] = False
                    report["failed_stages"].append(name)
                    logger.warning("Cleanup partial: stage=%s", name)
            except (Exception, asyncio.CancelledError) as error:
                report["complete"] = False
                report["failed_stages"].append(name)
                logger.error("Cleanup failed: stage=%s kind=%s", name, type(error).__name__)

        def sync_step(name: str, work: Callable[[], Any]) -> None:
            try:
                work()
            except Exception as error:
                report["complete"] = False
                report["failed_stages"].append(name)
                logger.error("Cleanup failed: stage=%s kind=%s", name, type(error).__name__)

        async def cleanup() -> None:
            started = asyncio.get_running_loop().time()
            if relay is not None:
                sync_step("relay-admission", relay.stop_admission)
            if definitions is not None:
                sync_step("indexer-admission", definitions.stop_admission)
            if scheduler is not None:
                sync_step("scheduler-admission", scheduler.stop_admission)
            # These owners join their real thread work before releasing any DB
            # or native resource. A cancelled await is never a thread-stop ack.
            await step("stream-searches", close_stream_searches)
            await step("source-searches", close_source_searches)
            # SP06/b: a keresések után nem indul új előtöltés; a futók az indexer-HTTP zárása előtt állnak le.
            await step("tech-info-prefetch", close_tech_info_prefetch)
            # SP07: a trackercache háttérfrissítései is az indexer-HTTP zárása előtt állnak le.
            await step("indexer-cache-refresh", close_indexer_cache_refresh)
            if definitions is not None:
                await step("relogins", definitions.close_logins)
            await step("producers", lambda: _cancel_producers(producers))
            if scheduler is not None:
                await step("scheduler", scheduler.aclose)
            await step("network-setup", close_network_setup)
            await step("background-db", drain_background_tasks)
            if relay is not None:
                await step("pieces", relay.close_piece_requests)
                await step("final-resume", relay.save_final_resume)
            if writer is not None:
                await step("resume-writer", writer.flush_and_close)
                report["resume_completed"] = writer.stats.completed
                report["resume_failed"] = writer.stats.failed
                report["resume_rejected"] = writer.stats.rejected
            if definitions is not None:
                await step("indexer-http", definitions.close_all)
            await step("metadata-http", tvdb_resolver.aclose)
            if unregister_resume is not None:
                sync_step("resume-callback", unregister_resume)
            if relay is not None:
                await step("native-session", relay.close_native)
            sync_step("playbacks", clear_active_playbacks)
            sync_step("playback-history", clear_playback_history_state)
            sync_step("stream-cache", invalidate_stream_cache)
            sync_step("indexer-cache", invalidate_indexer_cache)
            sync_step("origin-cache", clear_origin_cache)
            sync_step("indexer-factory", get_indexer_definitions_service.cache_clear)
            sync_step("relay-factory", get_relay_service.cache_clear)
            report["seconds"] = asyncio.get_running_loop().time()-started
            logger.info("Shutdown result: complete=%s failed_stages=%s overdue=%s", report["complete"], len(report["failed_stages"]), report["overdue"])

        async def grace_watchdog() -> None:
            await asyncio.sleep(30)
            report["complete"] = False
            report["overdue"] = True
            # Do not release resources beneath a live worker or pretend a
            # forced cancellation stopped native/DB work.
            logger.error("Shutdown grace exceeded: seconds=30; owned work still awaited")

        closing = asyncio.create_task(cleanup(), name="application-cleanup")
        watchdog = asyncio.create_task(grace_watchdog(), name="shutdown-grace")
        try:
            await await_owned_task(closing)
        finally:
            watchdog.cancel()
            await asyncio.gather(watchdog, return_exceptions=True)


def custom_generate_unique_id(route: APIRoute) -> str:
    method = next(iter(route.methods)).lower() if route.methods else "get"
    name = route.name

    if method == "head" and not name.startswith("head"):
        name = f"head_{name}"

    if route.tags:
        return f"{pydash.snake_case(route.tags[0])}_{name}"

    return name


app = FastAPI(
    title="StremHU Source",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

setup_exception_handlers(app)

app.add_middleware(StoppingPolicy)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    session_cookie="stremhu.source",
    secret_key=config.session_secret,
    max_age=60 * 60 * 24 * 30,
    https_only=True,
    same_site="lax",
)

app.add_middleware(SensitiveResponsePolicy)

app.include_router(api_router)

app.mount(
    "/",
    SPAStaticFiles(
        directory=config.client_path,
        html=True,
        check_dir=False,
    ),
    name="frontend",
)
