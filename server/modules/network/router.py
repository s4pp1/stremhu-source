from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.network.ddns.dependencies import get_ddns_service
from modules.network.ddns.schemas.api import DDNSProviderResponse
from modules.network.ddns.service import DDNSService
from modules.network.dependencies import get_network_service
from modules.network.schemas.api import NetworkSetupRequest, NetworkSetupResponse
from modules.network.service import NetworkService
from modules.roles.constants import UserRoleKey
from modules.settings.dependencies import get_settings_service
from modules.settings.schemas.api import NetworkSettingsResponse
from modules.settings.service import SettingsService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/network",
    tags=["Network"],
)


@router.get(
    "/settings",
    response_model=NetworkSettingsResponse,
)
def get_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    return settings_service.get_network()


@router.get(
    "/ddns/providers",
    response_model=list[DDNSProviderResponse],
)
def get_ddns_providers(
    ddns_service: DDNSService = Depends(get_ddns_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    return ddns_service.get_list()


@router.post(
    "/setup",
    response_model=NetworkSetupResponse,
)
async def setup(
    payload: NetworkSetupRequest,
    network_service: NetworkService = Depends(get_network_service),
    settings_service: SettingsService = Depends(get_settings_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    await network_service.setup(payload)
    return {
        "message": "Network setup started",
        "app_url": settings_service.get_app_url(),
    }
