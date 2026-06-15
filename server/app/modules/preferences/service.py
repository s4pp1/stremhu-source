from fastapi import HTTPException, status

from app.modules.preferences.models import PreferenceModel
from app.modules.preferences.repository import PreferencesRepository


class PreferencesService:
    def __init__(
        self,
        repository: PreferencesRepository,
    ):
        self._repository = repository

    def get_list(self, user_id: str | None = None) -> list[PreferenceModel]:
        return self._repository.find_list(user_id)

    def find_by_id(
        self,
        id: str,
        user_id: str | None = None,
    ) -> PreferenceModel | None:
        return self._repository.find_by_id(id, user_id)

    def get_by_id(
        self,
        id: str,
        user_id: str | None = None,
    ) -> PreferenceModel:
        preference = self._repository.find_by_id(id, user_id)

        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A kategória nem található.",
            )

        return preference

    def sync_to_db(self):
        self._repository.sync_to_db()
