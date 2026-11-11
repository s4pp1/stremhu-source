from collections.abc import Callable

from app.common.database import db_session
from app.common.logger import logger
from app.modules.relay.dependencies import get_relay_service
from app.modules.torrents.dependencies import create_torrents_service
from app.modules.torrents.resume_writer import ResumeWriter
from app.modules.torrents.service import TorrentsService


def _get_bg_service(db) -> TorrentsService:
    return create_torrents_service(db)


def register_persisted_torrents_callbacks(writer: ResumeWriter) -> Callable[[], None]:
    relay_service = get_relay_service()
    callback = writer.submit
    if callback not in relay_service.on_save_resume:
        relay_service.on_save_resume.append(callback)

    def unregister() -> None:
        try:
            relay_service.on_save_resume.remove(callback)
        except ValueError:
            pass

    return unregister


def restore_torrents() -> None:
    try:
        with db_session() as db:
            service = _get_bg_service(db)
            service.restore_torrents()
    except Exception as error:
        logger.error("Torrent restore failed: kind=%s", type(error).__name__)
