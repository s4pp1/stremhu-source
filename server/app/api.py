from fastapi import APIRouter

from app.config import show_internal_routes
from app.modules.attributes.router import router as attributes_router
from app.modules.auth.router import router as auth_router
from app.modules.indexers.router import router as indexers_router
from app.modules.kodi.router import router as kodi_router
from app.modules.me.router import router as me_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.network.router import router as network_router
from app.modules.pairings.router import router as pairings_router
from app.modules.playbacks.router import router as playbacks_router
from app.modules.preferences.router import router as preferences_router
from app.modules.relay_settings.router import router as relay_settings_router
from app.modules.stream.router import router as stream_router
from app.modules.stremio.router import router as stremio_router
from app.modules.system.router import router as system_router
from app.modules.torrents.router import router as torrents_router
from app.modules.users.router import router as users_router

api_router = APIRouter(prefix="/api")

# Modul routerek hozzáadása az API útválasztóhoz
api_router.include_router(
    attributes_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(
    preferences_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(monitoring_router)
api_router.include_router(
    auth_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(pairings_router)
api_router.include_router(
    users_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(
    me_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(
    system_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(relay_settings_router)
api_router.include_router(
    network_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(
    torrents_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(stream_router)
api_router.include_router(stremio_router)
api_router.include_router(kodi_router)
api_router.include_router(
    indexers_router,
    include_in_schema=show_internal_routes(),
)
api_router.include_router(
    playbacks_router,
    include_in_schema=show_internal_routes(),
)
