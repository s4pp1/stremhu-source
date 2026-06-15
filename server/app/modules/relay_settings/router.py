from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import SessionGuard
from app.modules.relay_settings.dependencies import get_relay_settings_service
from app.modules.relay_settings.service import RelaySettingsService
from app.modules.roles.constants import UserRoleKey
from app.modules.settings.schemas.api import (
    RelaySettingsResponse,
    RelaySettingsUpdateRequest,
)
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/relay",
    tags=["Relay"],
)


@router.get(
    "/settings",
    response_model=RelaySettingsResponse,
)
def get_settings(
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.get_settings()


@router.put(
    "/settings",
    response_model=RelaySettingsResponse,
)
def update_settings(
    payload: RelaySettingsUpdateRequest,
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.update_settings(payload)
