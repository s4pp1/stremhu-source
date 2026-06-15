from fastapi import HTTPException

from app.modules.attributes.service import AttributesService
from app.modules.preference_definitions.service import PreferenceDefinitionsService
from app.modules.preferences.schemas.internal import PreferenceCreate, PreferenceUpdate
from app.modules.system_preference_definitions.models import (
    SystemPreferenceDefinitionModel,
)
from app.modules.system_preference_definitions.repository import (
    SystemPreferenceDefinitionsRepository,
)


class SystemPreferenceDefinitionsService:
    def __init__(
        self,
        repository: SystemPreferenceDefinitionsRepository,
        preference_definitions_service: PreferenceDefinitionsService,
        attributes_service: AttributesService,
    ):
        self._repository = repository
        self._preference_definitions_service = preference_definitions_service
        self._attributes_service = attributes_service

    def find_list(self) -> list[SystemPreferenceDefinitionModel]:
        """Fetches all system preferences sorted by order priority with eager-loaded attributes."""
        return self._repository.find_list()

    def find_by_id(
        self,
        definition_id: str,
    ) -> SystemPreferenceDefinitionModel | None:
        """Retrieves a system preference model for a specific category type."""
        return self._repository.find_by_id(definition_id)

    def get_by_id(
        self,
        definition_id: str,
    ) -> SystemPreferenceDefinitionModel:
        system_preference_definition = self.find_by_id(
            definition_id,
        )
        if system_preference_definition is None:
            raise HTTPException(
                status_code=404,
                detail=f"A(z) '{definition_id}' preferenciája nem található.",
            )

        return system_preference_definition

    def create(
        self,
        preference_id: str,
        attribute_ids: list[str],
    ) -> SystemPreferenceDefinitionModel:
        """Creates a user's preference overrides, building the definition and attributes."""
        existing_preference_definition = self._repository.find_by_preference_id(
            preference_id
        )
        if existing_preference_definition:
            raise HTTPException(
                status_code=400,
                detail=f"A(z) '{preference_id}' preferenciája már létezik.",
            )

        preference_definition = self._preference_definitions_service.create(
            PreferenceCreate(
                preference_id=preference_id,
                attribute_ids=attribute_ids,
            )
        )

        system_preference_definitions = self.find_list()
        next_order = len(system_preference_definitions)

        return self._repository.create(
            preference_definition_id=preference_definition.id,
            order=next_order,
        )

    def update(
        self,
        definition_id: str,
        attribute_ids: list[str],
    ) -> SystemPreferenceDefinitionModel:
        """Updates the preferred attribute list of an existing user preference category."""
        preference_definition = self.get_by_id(definition_id)

        self._preference_definitions_service.update(
            preference_definition.definition_id,
            PreferenceUpdate(attribute_ids=attribute_ids),
        )

        return self.get_by_id(definition_id)

    def delete(
        self,
        definition_id: str,
    ) -> None:
        preference_definition = self.get_by_id(definition_id)

        self._repository.delete(preference_definition)

        self.reorder()

    def reorder(
        self,
        preference_ids: list[str] | None = None,
    ) -> list[SystemPreferenceDefinitionModel]:
        """Sets a new sorting priority list for the user's preference categories."""
        items = self.find_list()

        updates: list[tuple[SystemPreferenceDefinitionModel, int]] = []

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

        return self._repository.reorder(updates)
