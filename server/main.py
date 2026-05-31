import asyncio
import json
import logging
from contextlib import asynccontextmanager

import pydash
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from common.database import db_session
from config import NodeEnv, config
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from modules.attributes.dependencies import create_attributes_service
from modules.auth.router import router as auth_router
from modules.indexers.background_tasks import run_indexers_cleanup
from modules.indexers.router import router as indexers_router
from modules.kodi.router import router as kodi_router
from modules.me.router import router as me_router
from modules.monitoring.router import router as monitoring_router
from modules.network.router import router as network_router
from modules.pairings.background_tasks import run_expired_pairings_cleanup
from modules.pairings.router import router as pairings_router
from modules.preferences.service import PreferencesService
from modules.relay.background_tasks import alert_loop, resume_save_loop
from modules.relay.dependencies import get_relay_service
from modules.relay_settings.router import router as relay_settings_router
from modules.roles.dependencies import create_roles_service
from modules.settings.repository import SettingsRepository
from modules.settings.router import router as setting_router
from modules.settings.service import SettingsService
from modules.stream.router import router as stream_router
from modules.stremio.router import router as stremio_router
from modules.torrent_files.background_tasks import run_torrent_files_retention_cleanup
from modules.torrent_files.router import router as torrent_files_router
from modules.torrents.background_tasks import (
    register_persisted_torrents_callbacks,
)
from modules.torrents.router import router as torrents_router
from modules.users.router import router as users_router
from setproctitle import setproctitle
from starlette.middleware.sessions import SessionMiddleware

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

    # Beállítások és attribútumok inicializálása az adatbázisban és a libtorrent-ben induláskor
    network_service = None
    try:
        with db_session() as db:
            # 1. Szerepkörök szinkronizálása (elsőként, mert a felhasználók hivatkoznak rájuk)
            roles_service = create_roles_service(db)
            roles_service.sync_to_db()

            # 2. Preferenciák szinkronizálása (az attribútumok hivatkoznak rájuk)
            preferences_service = PreferencesService(db)
            preferences_service.sync_to_db()

            # 3. Attribútumok szinkronizálása
            attributes_service = create_attributes_service(db)
            attributes_service.sync_to_db()

            # 4. Indexer definíciók szinkronizálása
            from modules.indexer_definitions.dependencies import (
                get_indexer_definitions_service,
            )

            indexer_definitions_service = get_indexer_definitions_service()
            indexer_definitions_service.sync_to_db(db)

            settings_repository = SettingsRepository(db)
            settings_service = SettingsService(settings_repository)

            # Alkalmazzuk a mentett libtorrent beállításokat induláskor
            try:
                from modules.relay_settings.service import RelaySettingsService

                relay_settings_service = RelaySettingsService(
                    settings_service, get_relay_service()
                )
                relay_settings_service.sync_settings()
            except Exception as e:
                logging.getLogger("main").error(
                    f"🚨 Hiba történt a libtorrent beállítások szinkronizálása során induláskor: {e}"
                )

    except Exception as e:
        logging.getLogger("main").error(
            f"Nem sikerült a beállítások/attribútumok/indexerek inicializálása induláskor: {e}"
        )

    # Háttérfeladatok indítása
    alert_task = asyncio.create_task(alert_loop())
    save_task = asyncio.create_task(resume_save_loop())

    # APScheduler ütemező indítása
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_torrent_files_retention_cleanup,
        trigger="cron",
        hour=3,
        minute=0,
        id="torrent_files_cleanup",
        replace_existing=True,
    )
    scheduler.add_job(
        run_indexers_cleanup,
        trigger="cron",
        hour=4,
        minute=0,
        id="indexers_cleanup",
        replace_existing=True,
    )
    scheduler.add_job(
        run_expired_pairings_cleanup,
        trigger="cron",
        hour="*",
        minute=0,
        id="expired_pairings_cleanup",
        replace_existing=True,
    )
    if network_service:
        scheduler.add_job(
            network_service.sync_ip,
            trigger="interval",
            minutes=5,
            id="ddns_ip_sync",
            replace_existing=True,
        )
    scheduler.start()

    relay_service = get_relay_service()
    register_persisted_torrents_callbacks()

    priority_manager_task = asyncio.create_task(relay_service.priority_manager_loop())

    yield

    priority_manager_task.cancel()
    scheduler.shutdown()
    save_task.cancel()
    alert_task.cancel()

    relay_service.trigger_save_resume_data()

    await asyncio.sleep(1)
    relay_service.process_alerts()


app = FastAPI(
    title="StremHU Source",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    SessionMiddleware,
    session_cookie="stremhu.source",
    secret_key=config.session_secret,
    max_age=1000 * 60 * 60 * 24 * 30,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(monitoring_router)
api_router.include_router(auth_router)
api_router.include_router(pairings_router)
api_router.include_router(users_router)
api_router.include_router(me_router)
api_router.include_router(setting_router)
api_router.include_router(relay_settings_router)
api_router.include_router(network_router)
api_router.include_router(torrents_router)
api_router.include_router(torrent_files_router)
api_router.include_router(stream_router)
api_router.include_router(stremio_router)
api_router.include_router(kodi_router)
api_router.include_router(indexers_router)


app.include_router(api_router)


app.mount(
    "/",
    StaticFiles(
        directory=config.client_path,
        html=True,
    ),
    name="frontend",
)
