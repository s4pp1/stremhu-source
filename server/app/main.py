import asyncio
import json
from contextlib import asynccontextmanager

import pydash
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from setproctitle import setproctitle
from starlette.middleware.sessions import SessionMiddleware

from app.api import api_router
from app.common.logger import logger
from app.common.spa_static_files import SPAStaticFiles
from app.config import NodeEnv, config
from app.exceptions import setup_exception_handlers
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.relay.background_tasks import alert_loop, resume_save_loop
from app.modules.relay.dependencies import get_relay_service
from app.modules.torrents.background_tasks import (
    register_persisted_torrents_callbacks,
    restore_torrents,
)
from app.scheduler import setup_scheduler
from app.sync import sync_database_and_settings

setproctitle("stremhu-source")


@asynccontextmanager
async def lifespan(app: FastAPI):
    is_dev = config.node_env == NodeEnv.DEV

    if not is_dev:
        config.openapi_dir.mkdir(parents=True, exist_ok=True)
        with (config.openapi_dir / "openapi.json").open("w", encoding="utf-8") as f:
            json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

    sync_database_and_settings(app)

    alert_task = asyncio.create_task(alert_loop())
    save_task = asyncio.create_task(resume_save_loop())

    scheduler = setup_scheduler()
    scheduler.start()

    # 4. Libtorrent és perzisztált torrentek indítása, visszatöltése
    relay_service = get_relay_service()
    register_persisted_torrents_callbacks()
    restore_torrents()

    priority_manager_task = asyncio.create_task(relay_service.priority_manager_loop())

    yield

    # Leállítási szekvencia
    logger.info("🛑 Szerver leállítása, erőforrások felszabadítása...")

    indexer_definitions_service = get_indexer_definitions_service()

    await indexer_definitions_service.close_all()

    priority_manager_task.cancel()
    scheduler.shutdown()
    save_task.cancel()
    alert_task.cancel()

    relay_service.trigger_save_resume_data()

    await asyncio.sleep(1)
    relay_service.process_alerts()
    logger.info("✅ Leállítási szekvencia sikeresen lefutott.")


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
    max_age=1000 * 60 * 60 * 24 * 30,
)

# API router beemelése
app.include_router(api_router)


# Kliens statikus fájljainak kiszolgálása (SPA útválasztás támogatással)
app.mount(
    "/",
    SPAStaticFiles(
        directory=config.client_path,
        html=True,
    ),
    name="frontend",
)
