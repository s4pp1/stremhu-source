from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from itsdangerous import BadSignature
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexers.dependencies import create_indexers_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.stream.schemas import StreamToken
from app.modules.stream.service import StreamService
from app.modules.stream.utils.stream_token import parse_stream_token
from app.modules.torrent_files.dependencies import create_torrent_files_service
from app.modules.torrents.dependencies import create_torrents_service


def create_stream_service(db: Session) -> StreamService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    torrents_service = create_torrents_service(db)
    indexers_service = create_indexers_service(db)
    torrent_files_service = create_torrent_files_service(db)
    relay_service = get_relay_service()

    return StreamService(
        torrents_service=torrents_service,
        indexers_service=indexers_service,
        torrent_files_service=torrent_files_service,
        relay_service=relay_service,
    )


def get_stream_service(
    db: Annotated[Session, Depends(get_db)],
) -> StreamService:
    """FastAPI függőség-injektáló provider a StreamService példányosításához."""
    return create_stream_service(db)


def get_parsed_stream_token(
    stream_token: Annotated[str, Path(...)],
) -> StreamToken:
    try:
        return parse_stream_token(stream_token)
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Érvénytelen vagy lejárt stream token!",
        )
