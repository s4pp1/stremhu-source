from typing import Annotated

from fastapi import APIRouter, Depends

from core.modules.auth.dependencies import SessionGuard
from core.modules.network.ddns.dependencies import get_ddns_service
from core.modules.network.ddns.schemas.api import DDNSProviderResponse
from core.modules.network.ddns.service import DDNSService
from core.modules.network.dependencies import get_network_service
from core.modules.network.schemas.api import NetworkSetupRequest, NetworkSetupResponse
from core.modules.network.service import NetworkService
from core.modules.roles.constants import UserRoleKey
from core.modules.settings.dependencies import get_settings_service
from core.modules.settings.schemas.api import NetworkSettingsResponse
from core.modules.settings.service import SettingsService
from core.modules.users.models import UserModel

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
