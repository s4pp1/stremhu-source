from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class IndexerDefinitionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: str
    name: str
    url: str
    details_path: str
    requires_full_download: bool
