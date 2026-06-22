from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modules.attribute_exclusions.models import AttributeExclusionModel


class AttributeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str

    name: str

    short_name: str | None = None

    preference_id: str | None = None

    @classmethod
    def from_attribute_exclusion_model(
        cls,
        model: AttributeExclusionModel,
    ) -> "AttributeResponse":
        return cls(
            id=model.attribute.id,
            name=model.attribute.name,
            short_name=model.attribute.short_name,
            preference_id=model.attribute.preference_id,
        )
