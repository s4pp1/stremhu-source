from fastapi import HTTPException, status

from app.common.schemas.pagination import PaginationParams
from app.modules.playback_histories.models import PlaybackHistoryModel
from app.modules.playback_histories.repository import PlaybackHistoryRepository
from app.modules.playback_histories.schemas.internal import PlaybackHistoryCreate


class PlaybackHistoriesService:
    def __init__(self, repository: PlaybackHistoryRepository):
        self._repository = repository

    def create(
        self,
        payload: PlaybackHistoryCreate,
    ) -> PlaybackHistoryModel:
        self._ensure_not_exists(payload.playback_id)
        return self._repository.create(payload)

    def get_or_create(
        self,
        payload: PlaybackHistoryCreate,
    ) -> PlaybackHistoryModel:
        return self._repository.get_or_create(payload)

    def find_list(
        self,
        params: PaginationParams | None = None,
    ) -> tuple[list[PlaybackHistoryModel], int]:
        return self._repository.find_list(params)

    def find_by_id(self, playback_id: str) -> PlaybackHistoryModel | None:
        return self._repository.find_by_id(playback_id)

    def get_by_id(self, playback_id: str) -> PlaybackHistoryModel:
        return self._ensure_exists(playback_id)

    def delete(self, playback_id: str) -> None:
        playback_history = self.get_by_id(playback_id)
        self._repository.delete(playback_history)

    def _ensure_exists(
        self,
        playback_id: str,
    ) -> PlaybackHistoryModel:
        playback_history = self.find_by_id(playback_id)

        if playback_history is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ez a lejátszási előzmény nem létezik!",
            )

        return playback_history

    def _ensure_not_exists(
        self,
        playback_id: str,
    ) -> None:
        model = self.find_by_id(playback_id)

        if model is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ez a lejátszási előzmény már létezik!",
            )
