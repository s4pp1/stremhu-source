from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import SessionGuard
from app.modules.network.ddns.dependencies import get_ddns_service
from app.modules.network.ddns.schemas.api import DDNSProviderResponse
from app.modules.network.ddns.service import DDNSService
from app.modules.network.dependencies import get_network_service
from app.modules.network.schemas.api import NetworkSetupRequest, NetworkSetupResponse
from app.modules.network.service import NetworkService
from app.modules.roles.constants import UserRoleKey
from app.modules.settings.dependencies import get_settings_service
from app.modules.settings.schemas.api import NetworkSettingsResponse
from app.modules.settings.service import SettingsService
from app.modules.users.models import UserModel

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
