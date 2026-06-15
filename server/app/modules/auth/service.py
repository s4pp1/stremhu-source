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
