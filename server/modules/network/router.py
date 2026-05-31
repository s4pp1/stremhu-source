from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.network.dependencies import get_network_service
from modules.network.schemas import NetworkSetup
from modules.network.service import NetworkService
from modules.roles.enums import UserRole
from modules.users.models import UserModel

router = APIRouter(
    prefix="/network",
    tags=["Network"],
)


@router.post(
    "/config",
)
async def config(
    payload: NetworkSetup,
    network_service: NetworkService = Depends(get_network_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    await network_service.setup(payload)
    return {"message": "Network setup started"}
