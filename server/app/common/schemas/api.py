from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.common.schemas.internal import Success


class SuccessResponse(Success):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
