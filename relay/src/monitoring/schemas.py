from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Health(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    ok: bool = True
    start_time: float
