from fastapi import APIRouter
from modules.auth.router import router as auth_router
from modules.indexers.router import router as indexers_router
from modules.kodi.router import router as kodi_router
from modules.me.router import router as me_router
from modules.monitoring.router import router as monitoring_router
from modules.network.router import router as network_router
from modules.pairings.router import router as pairings_router
from modules.relay_settings.router import router as relay_settings_router
from modules.settings.router import router as setting_router
from modules.stream.router import router as stream_router
from modules.stremio.router import router as stremio_router
from modules.torrent_files.router import router as torrent_files_router
from modules.torrents.router import router as torrents_router
from modules.users.router import router as users_router

api_router = APIRouter(prefix="/api")

# Modul routerek hozzáadása az API útválasztóhoz
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
