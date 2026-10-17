from typing import Annotated

from fastapi import APIRouter, Depends

from core.common.schemas.api import SuccessResponse
from core.config import show_internal_routes
from core.modules.auth.dependencies import SessionGuard
from core.modules.pairings.dependencies import get_pairings_service
from core.modules.pairings.schemas.api import (
    PairInitResponse,
    PairStatusResponse,
    PairVerifyRequest,
)
from core.modules.pairings.service import PairingsService
from core.modules.users.models import UserModel

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
