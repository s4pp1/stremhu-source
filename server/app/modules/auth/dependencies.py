from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.auth.service import AuthService
from app.modules.users.dependencies import create_users_service, get_users_service
from app.modules.users.models import UserModel
from app.modules.users.service import UsersService


class SessionGuard:
    def __init__(self, allowed_roles: list[str] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        users_service: Annotated[UsersService, Depends(get_users_service)],
    ) -> UserModel:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nincs aktív bejelentkezési munkamenet.",
            )

        user = users_service.find_by_id(user_id)
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
        users_service: Annotated[UsersService, Depends(get_users_service)],
    ) -> UserModel | None:
        user_id = request.session.get("user_id")
        if not user_id:
            return None

        user = users_service.find_by_id(user_id)
        if not user:
            request.session.clear()
            return None

        return user


class ApiKeyGuard:
    def __init__(self, allowed_roles: list[str] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        request: Request,
        api_key: Annotated[str, Path(..., description="A felhasználó API kulcsa")],
        users_service: Annotated[UsersService, Depends(get_users_service)],
    ) -> UserModel:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Az API kulcs nincs megadva.",
            )

        user = users_service.find_by_api_key(api_key)
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


def create_auth_service(db: Session) -> AuthService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    users_service = create_users_service(db)
    return AuthService(users_service)


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
) -> AuthService:
    """FastAPI függőség-injektáló provider a AuthService példányosításához."""
    return create_auth_service(db)
