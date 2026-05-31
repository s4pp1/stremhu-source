from fastapi import APIRouter, Depends, HTTPException, Request, status
from modules.auth.dependencies import SessionGuard, get_auth_service
from modules.auth.schemas import LoginRequest, RegisterRequest
from modules.auth.service import AuthService
from modules.roles.enums import UserRole
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.schemas import User, UserCreateRequest
from modules.users.service import UsersService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    users_service: UsersService = Depends(get_users_service),
) -> UserModel:
    if users_service.count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A regisztráció le van tiltva, mert már létezik felhasználó a rendszerben.",
        )

    user_model = UserCreateRequest(
        username=payload.username,
        password=payload.password,
        role_id=UserRole.ADMIN,
    )
    return users_service.create(user_model)


@router.post(
    "/login",
    response_model=User,
)
def login(
    req: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    user = auth_service.validate(payload.username, payload.password)
    req.session["user_id"] = str(user.id)
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
def logout(
    req: Request,
    _: UserModel = Depends(SessionGuard()),
):
    req.session.clear()
    return {"message": "Sikeres kijelentkezés"}
