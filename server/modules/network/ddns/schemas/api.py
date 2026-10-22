from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DDNSProviderResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str

    name: str

    website_url: str

    domain_regex: str
