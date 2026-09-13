from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.settings.dependencies import create_settings_service
from app.modules.torznab.enums import TorznabErrorCode
from app.modules.torznab.exceptions import TorznabProtocolError
from app.modules.torznab.service import TorznabService
from app.modules.users.models import UserModel


def create_torznab_service(db: Session) -> TorznabService:
    settings_service = create_settings_service(db)

    return TorznabService(settings_service=settings_service)


def get_torznab_service(
    db: Annotated[Session, Depends(get_db)],
) -> TorznabService:
    return create_torznab_service(db)


def extract_api_key(request: Request) -> str | None:
    for raw_name, raw_value in request.query_params.multi_items():
        if raw_name.casefold() == "apikey" and raw_value:
            return raw_value

    return None


def require_torznab_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserModel:
    try:
        return auth_service.verify_api_key(extract_api_key(request))
    except HTTPException as error:
        raise TorznabProtocolError(
            TorznabErrorCode.INCORRECT_CREDENTIALS,
            "Incorrect user credentials",
        ) from error
