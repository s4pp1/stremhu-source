from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, status

from app.modules.users.models import UserModel
from app.modules.users.service import UsersService


class AuthService:
    def __init__(self, users_service: UsersService):
        self.users_service = users_service
        self.ph = PasswordHasher()

    def validate(self, username: str, password: str) -> UserModel:
        user = self.users_service.find_by_username(username)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hibás felhasználónév vagy jelszó",
            )

        try:
            self.ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hibás felhasználónév vagy jelszó",
            )

        return user

    def verify_api_key(
        self, api_key: str | None, allowed_roles: list[str] | None = None
    ) -> UserModel:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Az API kulcs nincs megadva.",
            )

        user = self.users_service.find_by_api_key(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A megadott API kulcs érvénytelen.",
            )

        if allowed_roles and user.role_id not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nincs jogosultságod a művelet végrehajtásához.",
            )

        return user
