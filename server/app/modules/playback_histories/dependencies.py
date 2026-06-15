from typing import Annotated
from app.common.database import get_db
from fastapi import Depends
from app.modules.playback_histories.repository import PlaybackHistoryRepository
from app.modules.playback_histories.service import PlaybackHistoriesService
from sqlalchemy.orm import Session


def create_playback_histories_service(db: Session) -> PlaybackHistoriesService:
    repository = PlaybackHistoryRepository(db)
    return PlaybackHistoriesService(repository)


def get_playback_histories_service(
    db: Annotated[Session, Depends(get_db)],
) -> PlaybackHistoriesService:
    return create_playback_histories_service(db)
