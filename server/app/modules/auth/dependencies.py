from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.session_origin import require_browser_origin
from app.modules.auth.service import AuthService
from app.modules.users.dependencies import create_users_service, get_users_service
from app.modules.users.models import UserModel
from app.modules.users.service import UsersService


def create_auth_service(db: Session) -> AuthService:
    users_service = create_users_service(db)
    return AuthService(users_service)


def get_auth_service(
    db: Annotated[Session, Depends(get_db, scope="function")],
) -> AuthService:
    return create_auth_service(db)


def _session_user(request: Request, users_service: UsersService) -> UserModel | None:
    require_browser_origin(request)
    user_id = request.session.get("user_id")
    epoch = request.session.get("session_epoch")
    # bool is an int subclass; signed legacy or malformed values are not epochs.
    if not isinstance(user_id, str) or not user_id or type(epoch) is not int:
        request.session.clear()
        return None
    user = users_service.find_by_id(user_id)
    if user is None or epoch != user.session_epoch:
        request.session.clear()
        return None
    return user


class SessionGuard:
    def __init__(self, allowed_roles: list[str] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        users_service: Annotated[UsersService, Depends(get_users_service)],
    ) -> UserModel:
        user = _session_user(request, users_service)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nincs aktív bejelentkezési munkamenet.",
            )

        if self.allowed_roles and user.role_id not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nincs jogosultságod a művelet végrehajtásához.",
            )

        return user


class OptionalSessionGuard:
    def __call__(
        self,
        request: Request,
        users_service: Annotated[UsersService, Depends(get_users_service)],
    ) -> UserModel | None:
        return _session_user(request, users_service)


class ApiKeyGuard:
    def __init__(self, allowed_roles: list[str] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        api_key: Annotated[str, Path(..., description="A felhasználó API kulcsa")],
        auth_service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> UserModel:
        return auth_service.verify_api_key(api_key, self.allowed_roles)
