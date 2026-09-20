import asyncio

from app.common.constants import BYTES_IN_GIGABYTE
from app.common.database import db_session
from app.common.logger import logger
from app.modules.indexers.dependencies import create_indexers_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.torrents.dependencies import create_torrents_service
from app.modules.torrents.service import TorrentsService


def handle_save_resume_data(info_hash: str, resume_bytes: bytes) -> None:
    try:
        with db_session() as db:
            service = _get_bg_service(db)
            service.save_resume_data(info_hash, resume_bytes)
    except Exception as e:
        logger.error(f"Hiba a resume adatok mentése során: {e}")


def _get_bg_service(db) -> TorrentsService:
    return create_torrents_service(db)


def register_persisted_torrents_callbacks() -> None:
    relay_service = get_relay_service()
    relay_service.on_save_resume.append(handle_save_resume_data)


def restore_torrents() -> None:
    try:
        with db_session() as db:
            service = _get_bg_service(db)
            service.restore_torrents()
    except Exception as e:
        logger.error(f"Hiba a torrentek visszaállítása során: {e}")


async def run_storage_quota_cleanup() -> None:
    """A tárhely kvótát túllépő torrentek takarítása (APScheduler-hez)."""

    try:
        with db_session() as db:
            settings_service = create_settings_service(db)
            system_settings = await asyncio.to_thread(settings_service.find_system)

            if system_settings is None or system_settings.max_storage_bytes <= 0:
                return

            torrents_service = create_torrents_service(db)
            used_bytes = await asyncio.to_thread(
                torrents_service.get_used_storage_bytes
            )

            if used_bytes <= system_settings.max_storage_bytes:
                return

            logger.info(
                "⏰ Tárhely kvóta túllépve (%.1f / %.1f GB), takarítás indítása...",
                used_bytes / BYTES_IN_GIGABYTE,
                system_settings.max_storage_bytes / BYTES_IN_GIGABYTE,
            )

            relay_service = get_relay_service()
            excluded_info_hashes = [
                stream.torrent.info_hash
                for stream in relay_service.get_active_streams()
            ]

            indexers_service = create_indexers_service(db)
            excluded_torrent_keys = (
                await indexers_service.find_hit_and_run_torrent_keys()
            )

            freed_bytes = await asyncio.to_thread(
                torrents_service.cleanup_storage_quota,
                system_settings.max_storage_bytes,
                excluded_info_hashes,
                excluded_torrent_keys,
            )

        logger.info(
            "✅ Tárhely takarítás befejeződött, %.1f GB szabadult fel.",
            freed_bytes / BYTES_IN_GIGABYTE,
        )
    except Exception:
        logger.exception("‼️ Hiba történt a tárhely takarítása során.")
