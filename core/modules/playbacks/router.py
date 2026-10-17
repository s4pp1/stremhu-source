from typing import Annotated

from fastapi import APIRouter, Depends

from core.common.schemas.pagination import Page, PaginationParams
from core.modules.auth.dependencies import SessionGuard
from core.modules.playback_histories.dependencies import get_playback_histories_service
from core.modules.playback_histories.schemas.api import PlaybackHistoryResponse
from core.modules.playback_histories.service import PlaybackHistoriesService
from core.modules.playbacks.dependencies import get_playbacks_service
from core.modules.playbacks.schemas.api import PlaybackResponse
from core.modules.playbacks.service import PlaybacksService
from core.modules.roles.constants import UserRoleKey
from core.modules.users.models import UserModel

router = APIRouter(prefix="/playbacks", tags=["Playbacks"])


@router.get(
    "/",
    response_model=list[PlaybackResponse],
)
def get_list(
    playbacks_service: Annotated[PlaybacksService, Depends(get_playbacks_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> list[PlaybackResponse]:
    active_playbacks = playbacks_service.get_active_playbacks()
    return [
        PlaybackResponse.from_playback(active_playback)
        for active_playback in active_playbacks
    ]


@router.get(
    "/history",
    response_model=Page[PlaybackHistoryResponse],
)
def get_history_list(
    playback_histories_service: Annotated[
        PlaybackHistoriesService, Depends(get_playback_histories_service)
    ],
    pagination_params: Annotated[PaginationParams, Depends()],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    items, total = playback_histories_service.find_list(pagination_params)
    return Page.create(
        items=items,
        total=total,
        params=pagination_params,
    )
