from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.network.dependencies import get_network_service
from modules.network.schemas.api import NetworkSetupRequest
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
):
    return settings_service.get_network()


@router.post(
    "/setup",
)
async def setup(
    payload: NetworkSetupRequest,
    network_service: NetworkService = Depends(get_network_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    await network_service.setup(payload)
    return {"message": "Network setup started"}


@router.delete(
    "/reset",
)
def reset(
    network_service: NetworkService = Depends(get_network_service),
    _: UserModel = Depends(SessionGuard([UserRoleKey.ADMIN])),
):
    network_service.setup_local()
    return {"message": "Network reset started"}
