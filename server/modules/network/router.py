from typing import Annotated

from fastapi import APIRouter, Depends

from server.modules.auth.dependencies import SessionGuard
from server.modules.network.ddns.dependencies import get_ddns_service
from server.modules.network.ddns.schemas.api import DDNSProviderResponse
from server.modules.network.ddns.service import DDNSService
from server.modules.network.dependencies import get_network_service
from server.modules.network.schemas.api import NetworkSetupRequest, NetworkSetupResponse
from server.modules.network.service import NetworkService
from server.modules.roles.constants import UserRoleKey
from server.modules.settings.dependencies import get_settings_service
from server.modules.settings.schemas.api import NetworkSettingsResponse
from server.modules.settings.service import SettingsService
from server.modules.users.models import UserModel

router = APIRouter(
    prefix="/network",
    tags=["Network"],
)


@router.get(
    "/settings",
    response_model=NetworkSettingsResponse,
)
def get_settings(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return settings_service.get_network()


@router.get(
    "/ddns/providers",
    response_model=list[DDNSProviderResponse],
)
def get_ddns_providers(
    ddns_service: Annotated[DDNSService, Depends(get_ddns_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return ddns_service.get_list()


@router.post(
    "/setup",
    response_model=NetworkSetupResponse,
)
async def setup(
    payload: NetworkSetupRequest,
    network_service: Annotated[NetworkService, Depends(get_network_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    await network_service.setup(payload)
    return {
        "message": "Network setup started",
        "app_url": settings_service.get_app_url(),
    }
