from common.schemas.internal import Success
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class SuccessResponse(Success):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
