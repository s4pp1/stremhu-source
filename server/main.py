import asyncio
import json
from contextlib import asynccontextmanager

import pydash
from api import api_router
from common.logger import logger
from config import NodeEnv, config
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from modules.relay.background_tasks import alert_loop, resume_save_loop
from modules.relay.dependencies import get_relay_service
from modules.torrents.background_tasks import (
    register_persisted_torrents_callbacks,
    restore_torrents,
)
from scheduler import setup_scheduler
from setproctitle import setproctitle
from starlette.middleware.sessions import SessionMiddleware
from sync import sync_database_and_settings

setproctitle("stremhu-source")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.node_env == NodeEnv.PRODUCTION:
        for route in app.routes:
            if isinstance(route, APIRoute):
                is_external = pydash.get(route, "openapi_extra.x-external") is True
                if not is_external:
                    route.include_in_schema = False

    out_dir = config.openapi_dir
    with (out_dir / "openapi.json").open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

    # 1. Rendszerindításkori szinkronizációk végrehajtása (szerepkörök, preferenciák, attribútumok, indexerek, libtorrent)
    sync_database_and_settings()

    # 2. Háttérfeladatok elindítása (alert_loop, resume_save_loop)
    alert_task = asyncio.create_task(alert_loop())
    save_task = asyncio.create_task(resume_save_loop())

    # 3. APScheduler beállítása és indítása (decentralizált moduláris háttérfeladatok regisztrálásával)
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

app.add_middleware(
    SessionMiddleware,
    session_cookie="stremhu.source",
    secret_key=config.session_secret,
    max_age=1000 * 60 * 60 * 24 * 30,
)

# API router beemelése
app.include_router(api_router)

# Kliens statikus fájljainak kiszolgálása
app.mount(
    "/",
    StaticFiles(
        directory=config.client_path,
        html=True,
    ),
    name="frontend",
)
