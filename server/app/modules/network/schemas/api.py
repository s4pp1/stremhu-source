from typing import Annotated

from app.modules.network.schemas.internal import (
    NetworkAutoSetup,
    NetworkLocalSetup,
    NetworkManualSetup,
)
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class NetworkLocalSetupRequest(NetworkLocalSetup):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class NetworkAutoSetupRequest(NetworkAutoSetup):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class NetworkManualSetupRequest(NetworkManualSetup):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


NetworkSetupRequest = Annotated[
    NetworkLocalSetupRequest | NetworkAutoSetupRequest | NetworkManualSetupRequest,
    Field(discriminator="mode"),
]


class NetworkSetupResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    app_url: str
    message: str
