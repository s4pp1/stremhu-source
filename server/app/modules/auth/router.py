from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.common.auth_rate_limit import admit_bootstrap, admit_login
from app.common.session_origin import browser_origin_dependency
from app.modules.auth.bootstrap import BootstrapService
from app.modules.auth.dependencies import SessionGuard, get_auth_service
from app.modules.auth.schemas.api import LoginRequest, RegisterRequest
from app.modules.auth.service import AuthService
from app.modules.users.models import UserModel
from app.modules.users.schemas.api import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    req: Request,
    payload: RegisterRequest,
    _: Annotated[None, Depends(browser_origin_dependency)],
) -> UserResponse:
    admit_bootstrap(req)
    snapshot = BootstrapService().register_first_admin(payload.username, payload.password)
    req.session.clear()
    req.session["user_id"] = snapshot.user.id
    req.session["session_epoch"] = snapshot.session_epoch
    return snapshot.user


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    req: Request,
    payload: LoginRequest,
    _: Annotated[None, Depends(browser_origin_dependency)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserModel:
    admit_login(req, payload.username)
    user = auth_service.validate(payload.username, payload.password)
    req.session.clear()
    req.session["user_id"] = user.id
    req.session["session_epoch"] = user.session_epoch
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
def logout(
    req: Request,
    _: Annotated[UserModel, Depends(SessionGuard())],
):
    req.session.clear()
    return {"message": "Sikeres kijelentkezés"}
