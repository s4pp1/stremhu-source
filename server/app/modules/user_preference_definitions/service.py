from fastapi import HTTPException

from app.modules.attributes.service import AttributesService
from app.modules.preference_definitions.service import PreferenceDefinitionsService
from app.modules.preferences.schemas.internal import PreferenceCreate, PreferenceUpdate
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel
from app.modules.user_preference_definitions.repository import (
    UserPreferenceDefinitionsRepository,
)


class UserPreferenceDefinitionsService:
    def __init__(
        self,
        repository: UserPreferenceDefinitionsRepository,
        preference_definitions_service: PreferenceDefinitionsService,
        attributes_service: AttributesService,
    ):
        self._repository = repository
        self._preference_definitions_service = preference_definitions_service
        self._attributes_service = attributes_service

    def find_list(self, user_id: str) -> list[UserPreferenceDefinitionModel]:
        """Fetches all preferences for a user, sorted by priority order."""
        return self._repository.find_list(user_id)

    def find_by_id(
        self,
        user_id: str,
        preference_id: str,
    ) -> UserPreferenceDefinitionModel | None:
        """Retrieves a user's preference model for a specific category type."""
        return self._repository.find_by_id(user_id, preference_id)

    def get_by_id(
        self,
        user_id: str,
        preference_id: str,
    ) -> UserPreferenceDefinitionModel:
        user_preference_definition = self.find_by_id(
            user_id,
            preference_id,
        )
        if user_preference_definition is None:
            raise HTTPException(
                status_code=404,
                detail=f"A(z) '{preference_id}' preferenciája nem található.",
            )

        return user_preference_definition

    def create(
        self,
        user_id: str,
        payload: PreferenceCreate,
    ) -> UserPreferenceDefinitionModel:
        """Creates a user's preference overrides, building the definition and attributes."""
        existing_preference_definition = self.find_by_id(user_id, payload.preference_id)
        if existing_preference_definition:
            raise HTTPException(
                status_code=400,
                detail=f"A(z) '{payload.preference_id}' preferenciája már létezik.",
            )

        preference_definition = self._preference_definitions_service.create(payload)

        user_preference_definitions = self.find_list(user_id)
        next_order = len(user_preference_definitions)

        return self._repository.create(
            user_id=user_id,
            preference_definition_id=preference_definition.id,
            order=next_order,
        )

    def update(
        self,
        user_id: str,
        preference_id: str,
        payload: PreferenceUpdate,
    ) -> UserPreferenceDefinitionModel:
        """Updates the preferred attribute list of an existing user preference category."""
        user_preference_definition = self.get_by_id(
            user_id,
            preference_id,
        )

        self._preference_definitions_service.update(
            user_preference_definition.definition_id,
            payload,
        )

        return self.get_by_id(user_id, preference_id)

    def delete(
        self,
        user_id: str,
        preference_id: str,
    ) -> None:
        user_preference_definition = self.get_by_id(
            user_id,
            preference_id,
        )

        self._repository.delete(user_preference_definition)

        self.reorder(user_id)

    def reorder(
        self,
        user_id: str,
        preference_ids: list[str] | None = None,
    ) -> list[UserPreferenceDefinitionModel]:
        """Sets a new sorting priority list for the user's preference categories."""
        items = self.find_list(user_id)

        updates: list[tuple[UserPreferenceDefinitionModel, int]] = []

        if preference_ids is not None:
            item_map = {item.definition.preference_id: item for item in items}
            for pref in preference_ids:
                if pref not in item_map:
                    raise HTTPException(
                        status_code=400,
                        detail=f"A(z) '{pref}' preferencia nem található.",
                    )

            for idx, preference_id in enumerate(preference_ids):
                updates.append((item_map[preference_id], idx))
        else:
            for idx, item in enumerate(items):
                updates.append((item, idx))

        return self._repository.reorder(user_id, updates)
