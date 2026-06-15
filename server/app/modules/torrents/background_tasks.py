from app.common.database import db_session
from app.common.logger import logger
from app.modules.relay.dependencies import get_relay_service
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
