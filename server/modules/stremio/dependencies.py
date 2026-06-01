from common.database import get_db
from fastapi import Depends, Path
from modules.network.dependencies import create_network_service
from modules.stremio.schemas import ParsedCatalogId, ParsedExtra, ParsedStreamId
from modules.stremio.service import StremioService
from modules.stremio.utils import parse_catalog_id, parse_extra, parse_stream_id
from modules.torrent_streams.dependencies import create_torrent_streams_service
from sqlalchemy.orm import Session


def create_stremio_service(db: Session) -> StremioService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    torrent_streams_service = create_torrent_streams_service(db)
    network_service = create_network_service(db)
    return StremioService(
        torrent_streams_service=torrent_streams_service,
        network_service=network_service,
    )


def get_stremio_service(
    db: Session = Depends(get_db),
) -> StremioService:
    """FastAPI függőség-injektáló provider a StremioService példányosításához."""
    return create_stremio_service(db)


def get_parsed_stream_id(
    stream_id: str = Path(
        ..., description="Stream azonosító (IMDB ID vagy torrent ID)"
    ),
) -> ParsedStreamId:
    """Automatikus parse-olás a Stremio stream azonosítóhoz (pl. tt1234567, stremhu-source:tracker:id)."""
    return parse_stream_id(stream_id)


def get_parsed_catalog_id(
    meta_id: str = Path(
        ..., description="Katalógus / Meta azonosító (trackerId:torrentId)"
    ),
) -> ParsedCatalogId | None:
    """Automatikus parse-olás a Stremio catalog / meta azonosítóhoz (pl. trackerId:torrentId)."""
    return parse_catalog_id(meta_id)


def get_parsed_extra(
    extra: str = Path(
        ..., description="Kiegészítő szűrési paraméterek (pl. search=film&skip=20)"
    ),
) -> ParsedExtra:
    """Automatikus parse-olás a Stremio extra (pl. search/skip) paraméterekhez."""
    return parse_extra(extra)
