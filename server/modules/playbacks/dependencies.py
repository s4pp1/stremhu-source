from typing import Annotated

from fastapi import Depends

from server.modules.playback_histories.dependencies import (
    get_playback_histories_service,
)
from server.modules.playback_histories.service import PlaybackHistoriesService
from server.modules.playbacks.service import PlaybacksService
from server.modules.relay.dependencies import get_relay_service
from server.modules.relay.service import RelayService


def create_playbacks_service(
    relay_service: RelayService,
    playback_histories_service: PlaybackHistoriesService,
) -> PlaybacksService:
    return PlaybacksService(
        relay_service=relay_service,
        playback_histories_service=playback_histories_service,
    )


def get_playbacks_service(
    relay_service: Annotated[RelayService, Depends(get_relay_service)],
    playback_histories_service: Annotated[
        PlaybackHistoriesService, Depends(get_playback_histories_service)
    ],
) -> PlaybacksService:
    return create_playbacks_service(
        relay_service=relay_service,
        playback_histories_service=playback_histories_service,
    )
