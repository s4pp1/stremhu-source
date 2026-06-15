from fastapi import HTTPException, status

from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.attribute_exclusions.repository import AttributeExclusionsRepository
from app.modules.attribute_exclusions.schemas.internal import (
    AttributeExclusionCreate,
    AttributeExclusionFilter,
)


class AttributeExclusionsService:
    def __init__(
        self,
        repository: AttributeExclusionsRepository,
    ):
        self.repository = repository

    def create(
        self,
        payload: AttributeExclusionCreate,
    ) -> AttributeExclusionModel:
        self._ensure_not_exists(payload.attribute_id, payload.user_id)

        model = self.repository.create(payload)
        return model

    def find_list(
        self,
        filter: AttributeExclusionFilter | None = None,
    ) -> list[AttributeExclusionModel]:
        return self.repository.find_list(filter)

    def find_by_id(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> AttributeExclusionModel | None:
        return self.repository.find_by_id(attribute_id, user_id)

    def get_by_id(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> AttributeExclusionModel:
        return self._ensure_exists(attribute_id, user_id)

    def delete(self, attribute_id: str, user_id: str | None) -> None:
        self._ensure_exists(attribute_id, user_id)
        self.repository.delete(attribute_id, user_id)

    def _ensure_exists(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> AttributeExclusionModel:
        model = self.find_by_id(
            attribute_id=attribute_id,
            user_id=user_id,
        )

        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ez a kizárás nem létezik!",
            )

        return model

    def _ensure_not_exists(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> None:
        model = self.find_by_id(
            attribute_id=attribute_id,
            user_id=user_id,
        )

        if model is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ez a kizárás már létezik!",
            )
