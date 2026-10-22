from typing import Annotated

from fastapi import APIRouter, Depends

from server.common.schemas.api import SuccessResponse
from server.config import show_internal_routes
from server.modules.auth.dependencies import SessionGuard
from server.modules.pairings.dependencies import get_pairings_service
from server.modules.pairings.schemas.api import (
    PairInitResponse,
    PairStatusResponse,
    PairVerifyRequest,
)
from server.modules.pairings.service import PairingsService
from server.modules.users.models import UserModel

router = APIRouter(prefix="/auth/pair", tags=["Pairing"])


@router.post(
    "/init",
    response_model=PairInitResponse,
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
    include_in_schema=show_internal_routes(),
)
def verify(
    payload: PairVerifyRequest,
    current_user: Annotated[UserModel, Depends(SessionGuard())],
    pairings_service: Annotated[PairingsService, Depends(get_pairings_service)],
):
    """4 jegyű párosító kód jóváhagyása a bejelentkezett felhasználó által."""
    result = pairings_service.authorize_pairing_code(payload.user_code, current_user)
    return result
