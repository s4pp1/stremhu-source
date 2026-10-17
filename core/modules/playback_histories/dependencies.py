from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.playback_histories.repository import PlaybackHistoryRepository
from core.modules.playback_histories.service import PlaybackHistoriesService


def create_playback_histories_service(db: Session) -> PlaybackHistoriesService:
    repository = PlaybackHistoryRepository(db)
    return PlaybackHistoriesService(repository)


def get_playback_histories_service(
    db: Annotated[Session, Depends(get_db)],
) -> PlaybackHistoriesService:
    return create_playback_histories_service(db)
