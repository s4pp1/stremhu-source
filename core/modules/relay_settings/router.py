from typing import Annotated

from fastapi import APIRouter, Depends

from core.config import show_internal_routes
from core.modules.auth.dependencies import ApiKeyGuard, SessionGuard
from core.modules.relay_settings.dependencies import get_relay_settings_service
from core.modules.relay_settings.service import RelaySettingsService
from core.modules.roles.constants import UserRoleKey
from core.modules.settings.schemas.api import (
    RelaySettingsResponse,
    RelaySettingsUpdateRequest,
)
from core.modules.users.models import UserModel

router = APIRouter(
    tags=["Relay"],
)


@router.get(
    "/relay/settings",
    response_model=RelaySettingsResponse,
    include_in_schema=show_internal_routes(),
)
def get_settings(
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.get_settings()


@router.put(
    "/relay/settings",
    response_model=RelaySettingsResponse,
    include_in_schema=show_internal_routes(),
)
def update_settings(
    payload: RelaySettingsUpdateRequest,
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.update_settings(payload)


@router.get(
    "/{api_key}/relay/settings",
    response_model=RelaySettingsResponse,
)
def get_settings_with_api_key(
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(ApiKeyGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.get_settings()


@router.put(
    "/{api_key}/relay/settings",
    response_model=RelaySettingsResponse,
)
def update_settings_with_api_key(
    payload: RelaySettingsUpdateRequest,
    relay_settings_service: Annotated[
        RelaySettingsService, Depends(get_relay_settings_service)
    ],
    _: Annotated[UserModel, Depends(ApiKeyGuard([UserRoleKey.ADMIN]))],
):
    return relay_settings_service.update_settings(payload)
