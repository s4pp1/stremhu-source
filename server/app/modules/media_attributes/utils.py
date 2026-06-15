from app.modules.attributes.models import AttributeModel
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES

ATTRIBUTES_MAP = {attribute.id: attribute for attribute in DEFAULT_ATTRIBUTES}


def resolve_attribute_ids(attribute_ids: list[str]) -> list[AttributeModel]:
    """Resolves a list of attribute IDs to their corresponding AttributeModel instances from the DEFAULT_ATTRIBUTES."""
    return [
        ATTRIBUTES_MAP[attribute_id]
        for attribute_id in attribute_ids
        if attribute_id in ATTRIBUTES_MAP
    ]
