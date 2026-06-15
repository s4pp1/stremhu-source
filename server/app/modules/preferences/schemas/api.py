from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.attributes.schemas.api import AttributeResponse
from app.modules.preferences.schemas.internal import (
    PreferenceCreate,
    PreferencesReorder,
    PreferenceUpdate,
)
from app.modules.system_preference_definitions.models import (
    SystemPreferenceDefinitionModel,
)
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    name: str
    description: str
    emoji: str | None
    attributes: list[AttributeResponse]

    @classmethod
    def from_user_preference_definition_model(
        cls,
        user_preference_definition_model: UserPreferenceDefinitionModel,
    ) -> "PreferenceResponse":
        return cls(
            id=user_preference_definition_model.definition.preference.id,
            name=user_preference_definition_model.definition.preference.name,
            description=user_preference_definition_model.definition.preference.description,
            emoji=user_preference_definition_model.definition.preference.emoji,
            attributes=[
                AttributeResponse.model_validate(definition_attribute.attribute)
                for definition_attribute in user_preference_definition_model.definition.definition_attributes
            ],
        )

    @classmethod
    def from_system_preference_definition_model(
        cls,
        system_preference_definition_model: SystemPreferenceDefinitionModel,
    ) -> "PreferenceResponse":
        return cls(
            id=system_preference_definition_model.definition.preference.id,
            name=system_preference_definition_model.definition.preference.name,
            description=system_preference_definition_model.definition.preference.description,
            emoji=system_preference_definition_model.definition.preference.emoji,
            attributes=[
                AttributeResponse.model_validate(definition_attribute.attribute)
                for definition_attribute in system_preference_definition_model.definition.definition_attributes
            ],
        )


class PreferenceCreateRequest(PreferenceCreate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class PreferenceUpdateRequest(PreferenceUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class PreferencesReorderRequest(PreferencesReorder):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
