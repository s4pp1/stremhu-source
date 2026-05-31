from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.pairings.dependencies import get_pairings_service
from modules.pairings.schemas import (
    PairInit,
    PairStatus,
    PairStatusRequest,
    PairVerify,
    PairVerifyRequest,
)
from modules.pairings.service import PairingsService
from modules.users.models import UserModel

router = APIRouter(prefix="/auth/pair", tags=["Pairing"])


@router.post(
    "/init",
    response_model=PairInit,
    openapi_extra={"x-external": True},
)
def init(
    pairings_service: PairingsService = Depends(get_pairings_service),
) -> PairInit:
    """Új eszközpárosítási folyamat kezdeményezése."""
    result = pairings_service.generate_pairing_codes()
    return PairInit.model_validate(result)


@router.post(
    "/status",
    response_model=PairStatus,
    openapi_extra={"x-external": True},
)
def status(
    payload: PairStatusRequest,
    pairings_service: PairingsService = Depends(get_pairings_service),
) -> PairStatus:
    """Eszköz párosítási státuszának lekérdezése."""
    result = pairings_service.poll_pairing_status(payload.device_code)
    return PairStatus.model_validate(result)


@router.post(
    "/verify",
    response_model=PairVerify,
)
def verify(
    payload: PairVerifyRequest,
    current_user: UserModel = Depends(SessionGuard()),
    pairings_service: PairingsService = Depends(get_pairings_service),
) -> PairVerify:
    """4 jegyű párosító kód jóváhagyása a bejelentkezett felhasználó által."""
    result = pairings_service.authorize_pairing_code(payload.user_code, current_user)
    return PairVerify.model_validate(result)
