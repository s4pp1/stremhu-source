import pydash
from fastapi import HTTPException

from app.modules.attributes.service import AttributesService
from app.modules.preference_definitions.models import PreferenceDefinitionModel
from app.modules.preference_definitions.repository import PreferenceDefinitionRepository
from app.modules.preferences.schemas.internal import PreferenceCreate, PreferenceUpdate


class PreferenceDefinitionsService:
    def __init__(
        self,
        repository: PreferenceDefinitionRepository,
        attributes_service: AttributesService,
    ):
        self._repository = repository
        self._attributes_service = attributes_service

    def create(
        self,
        payload: PreferenceCreate,
    ) -> PreferenceDefinitionModel:

        self._validate_attribute_ids(payload.preference_id, payload.attribute_ids)

        return self._repository.create(payload)

    def find_by_id(
        self, preference_definition_id: str
    ) -> PreferenceDefinitionModel | None:
        preference_definition = self._repository.find_by_id(preference_definition_id)
        return preference_definition

    def get_by_id(self, preference_definition_id: str) -> PreferenceDefinitionModel:
        preference_definition = self.find_by_id(preference_definition_id)
        if not preference_definition:
            raise HTTPException(
                status_code=404,
                detail=f"A(z) '{preference_definition_id}' preferenciája nem található.",
            )
        return preference_definition

    def update(
        self,
        preference_definition_id: str,
        payload: PreferenceUpdate,
    ) -> PreferenceDefinitionModel:
        preference_definition = self.find_by_id(preference_definition_id)
        if not preference_definition:
            raise HTTPException(
                status_code=404,
                detail=f"A(z) '{preference_definition_id}' preferenciája nem található.",
            )

        self._validate_attribute_ids(
            preference_definition.preference_id,
            payload.attribute_ids,
        )

        return self._repository.update(
            preference_definition_id,
            payload.attribute_ids,
        )

    def delete(self, preference_definition_id: str) -> None:
        preference_definition = self.get_by_id(preference_definition_id)
        self._repository.delete(preference_definition.id)

    def _validate_attribute_ids(
        self, preference_id: str, attribute_ids: list[str]
    ) -> None:
        """Validates that all provided attribute IDs are unique and belong to the given preference category."""
        if pydash.duplicates(attribute_ids):
            raise HTTPException(
                status_code=400,
                detail="Egy attribútum nem szerepelhet többször ugyanazon preferencián belül.",
            )

        db_attributes = self._attributes_service.get_by_preference(preference_id)
        valid_attribute_ids = {attr.id for attr in db_attributes}
        for attribute_id in attribute_ids:
            if attribute_id not in valid_attribute_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"A(z) '{attribute_id}' attribútum nem tartozik a(z) '{preference_id}' preferenciához.",
                )
