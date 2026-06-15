from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.modules.auth.dependencies import SessionGuard, get_auth_service
from app.modules.auth.schemas.api import LoginRequest, RegisterRequest
from app.modules.auth.service import AuthService
from app.modules.roles.constants import UserRoleKey
from app.modules.users.dependencies import get_users_service
from app.modules.users.models import UserModel
from app.modules.users.schemas.api import UserResponse
from app.modules.users.schemas.internal import UserCreate
from app.modules.users.service import UsersService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    req: Request,
    payload: RegisterRequest,
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserModel:
    if users_service.count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A regisztráció le van tiltva, mert már létezik felhasználó a rendszerben.",
        )

    user_model = UserCreate(
        username=payload.username,
        password=payload.password,
        role_id=UserRoleKey.ADMIN,
    )
    user = users_service.create(user_model)

    req.session["user_id"] = user.id

    return user


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    req: Request,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserModel:
    user = auth_service.validate(payload.username, payload.password)
    req.session["user_id"] = user.id
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
