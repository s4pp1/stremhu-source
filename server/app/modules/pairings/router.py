from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.schemas.api import SuccessResponse
from app.modules.auth.dependencies import SessionGuard
from app.modules.pairings.dependencies import get_pairings_service
from app.modules.pairings.schemas.api import (
    PairInitResponse,
    PairStatusResponse,
    PairVerifyRequest,
)
from app.modules.pairings.service import PairingsService
from app.modules.users.models import UserModel

router = APIRouter(prefix="/auth/pair", tags=["Pairing"])


@router.post(
    "/init",
    response_model=PairInitResponse,
    openapi_extra={"x-external": True},
)
def init(
    pairings_service: Annotated[PairingsService, Depends(get_pairings_service)],
):
    """Új eszközpárosítási folyamat kezdeményezése."""
    result = pairings_service.generate_pairing_codes()
    return result


@router.get(
    "/status/{device_code}",
    response_model=PairStatusResponse,
    openapi_extra={"x-external": True},
)
def status(
    device_code: str,
    pairings_service: Annotated[PairingsService, Depends(get_pairings_service)],
):
    """Eszköz párosítási státuszának lekérdezése."""
    result = pairings_service.poll_pairing_status(device_code)
    return result


@router.post(
    "/verify",
    response_model=SuccessResponse,
)
def verify(
    payload: PairVerifyRequest,
    current_user: Annotated[UserModel, Depends(SessionGuard())],
    pairings_service: Annotated[PairingsService, Depends(get_pairings_service)],
):
    """4 jegyű párosító kód jóváhagyása a bejelentkezett felhasználó által."""
    result = pairings_service.authorize_pairing_code(payload.user_code, current_user)
    return result
