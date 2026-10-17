from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.kodi.service import KodiService
from core.modules.torrent_streams.dependencies import (
    create_torrent_streams_service,
)


def create_kodi_service(
    db: Session,
) -> KodiService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    torrent_streams_service = create_torrent_streams_service(db)
    return KodiService(torrent_streams_service=torrent_streams_service)


def get_kodi_service(
    db: Annotated[Session, Depends(get_db)],
) -> KodiService:
    """FastAPI függőség-injektáló provider a KodiService példányosításához."""
    return create_kodi_service(db)
