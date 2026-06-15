from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.modules.settings.enums import NetworkConnectionEnum, NetworkModeEnum


class NetworkLocalSetup(BaseModel):
    mode: Literal[NetworkModeEnum.LOCAL]


class NetworkAutoSetup(BaseModel):
    mode: Literal[NetworkModeEnum.AUTO]
    host: str
    connection: NetworkConnectionEnum
    provider: str
    token: str
    email: str


class NetworkManualSetup(BaseModel):
    mode: Literal[NetworkModeEnum.MANUAL]
    host: str


NetworkSetup = Annotated[
    NetworkLocalSetup | NetworkAutoSetup | NetworkManualSetup,
    Field(discriminator="mode"),
]
