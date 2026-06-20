from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES

ATTRIBUTES_MAP = {attribute.id: attribute for attribute in DEFAULT_ATTRIBUTES}


def resolve_attribute_ids(attribute_ids: list[str]) -> list[MediaAttributeModel]:
    return [
        ATTRIBUTES_MAP[attribute_id]
        for attribute_id in attribute_ids
        if attribute_id in ATTRIBUTES_MAP
    ]
