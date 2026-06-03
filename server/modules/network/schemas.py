from typing import Annotated, Literal

from modules.settings.enums import NetworkConnectionEnum, NetworkModeEnum
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class NetworkAutoSetup(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.AUTO]
    host: str
    connection: NetworkConnectionEnum
    provider: str
    token: str
    email: str


class NetworkManualSetup(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.MANUAL]
    host: str
    reverse_proxy: bool


NetworkSetup = Annotated[
    NetworkAutoSetup | NetworkManualSetup,
    Field(discriminator="mode"),
]
