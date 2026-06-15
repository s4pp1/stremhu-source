from fastapi import HTTPException, status

from app.modules.playback_histories.service import PlaybackHistoriesService
from app.modules.playbacks.schemas.internal import Playback
from app.modules.relay.service import RelayService
from app.modules.users.models import UserModel


class PlaybacksService:
    def __init__(
        self,
        relay_service: RelayService,
        playback_histories_service: PlaybackHistoriesService,
    ):
        self._relay_service = relay_service
        self._playback_histories_service = playback_histories_service

    def get_active_playbacks(self) -> list[Playback]:
        active_streams = self._relay_service.get_active_streams()
        streams_by_playback = {stream.playback_id: stream for stream in active_streams}

        active_playbacks: list[Playback] = []

        for playback_id, stream in streams_by_playback.items():
            history = self._playback_histories_service.find_by_id(playback_id)

            if history is None:
                continue

            active_playbacks.append(
                Playback(
                    playback_history_model=history,
                    stream=stream,
                )
            )

        return active_playbacks

    def check_playback_limit(
        self,
        user: UserModel,
        current_playback_id: str,
    ) -> None:
        if user.max_concurrent_streams is None:
            return

        active_streams = self._relay_service.get_active_streams()

        user_playback_ids = {
            stream.playback_id
            for stream in active_streams
            if stream.user_id == user.id and stream.playback_id != current_playback_id
        }

        if len(user_playback_ids) >= user.max_concurrent_streams:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Elérted a maximálisan engedélyezett egyidejű lejátszások számát!",
            )
