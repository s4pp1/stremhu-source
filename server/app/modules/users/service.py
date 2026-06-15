import uuid
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from fastapi import HTTPException, status

from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.attribute_exclusions.schemas.api import AttributeExclusionCreateRequest
from app.modules.attribute_exclusions.schemas.internal import (
    AttributeExclusionCreate,
    AttributeExclusionFilter,
)
from app.modules.attribute_exclusions.service import AttributeExclusionsService
from app.modules.media_attributes.schemas.internal import MediaAttributeFilter
from app.modules.roles.constants import UserRoleKey
from app.modules.users.models import UserModel
from app.modules.users.repository import UsersRepository
from app.modules.users.schemas.internal import UserCreate, UserUpdate

if TYPE_CHECKING:
    from app.modules.media_attributes.models import MediaAttributeModel
    from app.modules.media_attributes.service import MediaAttributesService


class UsersService:
    def __init__(
        self,
        users_repository: UsersRepository,
        attribute_exclusions_service: AttributeExclusionsService,
        media_attributes_service: "MediaAttributesService",
    ):
        self._users_repository = users_repository
        self._attribute_exclusions_service = attribute_exclusions_service
        self._media_attributes_service = media_attributes_service

    def get_list(self) -> list[UserModel]:
        return self._users_repository.find_list()

    def create(
        self,
        payload: UserCreate,
    ) -> UserModel:
        self._check_exist_username(payload.username)

        password_hash = None
        if payload.password is not None:
            password_hash = self._hash_password(payload.password)
        elif payload.role_id != UserRoleKey.USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jelszó nélkül csak sima felhasználó hozható létre!",
            )

        user = UserModel(
            username=payload.username,
            password_hash=password_hash,
            role_id=payload.role_id,
            api_key=str(uuid.uuid4()),
            torrent_seed=payload.torrent_seed,
            only_best_torrent=payload.only_best_torrent,
        )

        return self._users_repository.create(user)

    def find_by_id(self, id: str) -> UserModel | None:
        return self._users_repository.find_by_id(id)

    def get_by_id(self, id: str) -> UserModel:
        user = self.find_by_id(id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A felhasználó nem található.",
            )
        return user

    def find_by_username(self, username: str) -> UserModel | None:
        return self._users_repository.find_by_username(username)

    def find_by_api_key(self, api_key: str) -> UserModel | None:
        return self._users_repository.find_by_api_key(api_key)

    def count(self) -> int:
        return self._users_repository.count()

    def update(
        self,
        user_id: str,
        payload: UserUpdate,
    ) -> UserModel:
        user = self.get_by_id(user_id)

        update_data = payload.model_dump(exclude_unset=True)

        if "username" in update_data:
            self._check_exist_username(update_data["username"])

        if "password" in update_data:
            password = update_data.pop("password")
            if password is not None:
                user.password_hash = self._hash_password(password)
            else:
                user.password_hash = None

        for key, value in update_data.items():
            setattr(user, key, value)

        return self._users_repository.create(user)

    def regenerate_api_key(self, user_id: str) -> UserModel:
        user = self.get_by_id(user_id)
        user.api_key = str(uuid.uuid4())
        return self._users_repository.create(user)

    def delete(self, user_id: str, current_user: UserModel) -> None:
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Saját fiókod törlésére nincs lehetőség!",
            )

        self.get_by_id(user_id)
        self._users_repository.delete(user_id)

    def get_attributes(self, user_id: str) -> list["MediaAttributeModel"]:
        return self._media_attributes_service.find_list(
            MediaAttributeFilter(
                user_id=user_id,
                not_added_to_preference=True,
            ),
        )

    def create_attribute_exclusion(
        self, user_id: str, payload: AttributeExclusionCreateRequest
    ) -> AttributeExclusionModel:
        return self._attribute_exclusions_service.create(
            AttributeExclusionCreate(
                user_id=user_id,
                attribute_id=payload.attribute_id,
            ),
        )

    def get_attribute_exclusions(self, user_id: str) -> list[AttributeExclusionModel]:
        return self._attribute_exclusions_service.find_list(
            AttributeExclusionFilter(
                user_id=user_id,
            ),
        )

    def _check_exist_username(self, username: str) -> None:
        existing_user = self._users_repository.find_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ez a felhasználónév már foglalt.",
            )

    def _hash_password(self, password: str) -> str:
        ph = PasswordHasher()
        return ph.hash(password)
