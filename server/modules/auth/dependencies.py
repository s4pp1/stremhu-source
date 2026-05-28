from fastapi import Depends, HTTPException, Path, Request, status
from modules.auth.service import AuthService
from modules.roles.enums import UserRole
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.service import UsersService


class SessionGuard:
    def __init__(self, allowed_roles: list[UserRole] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        users_service: UsersService = Depends(get_users_service),
    ) -> UserModel:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nincs aktív bejelentkezési munkamenet.",
            )

        user = users_service.get_by_id(user_id)
        if not user:
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A munkamenethez tartozó felhasználó nem található.",
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
        users_service: UsersService = Depends(get_users_service),
    ) -> UserModel | None:
        user_id = request.session.get("user_id")
        if not user_id:
            return None

        user = users_service.get_by_id(user_id)
        if not user:
            request.session.clear()
            return None

        return user


class ApiKeyGuard:
    def __init__(self, allowed_roles: list[UserRole] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        api_key: str = Path(..., description="A felhasználó API kulcsa"),
        users_service: UsersService = Depends(get_users_service),
    ) -> UserModel:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Az API kulcs nincs megadva.",
            )

        user = users_service.get_by_token(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A megadott API kulcs érvénytelen.",
            )

        if self.allowed_roles and user.role_id not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nincs jogosultságod a művelet végrehajtásához.",
            )

        return user


def get_auth_service(
    users_service: UsersService = Depends(get_users_service),
) -> AuthService:
    return AuthService(users_service)
