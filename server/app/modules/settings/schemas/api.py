from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.modules.settings.enums import NetworkConnectionEnum, NetworkModeEnum
from app.modules.settings.schemas.internal import (
    NetworkManualSettings,
    RelaySettingsUpdate,
    SystemSettingsUpdate,
)


class SystemSettingsResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    hit_and_run: bool
    keep_seed_seconds: int
    cache_retention_seconds: int


class SystemSettingsUpdateRequest(SystemSettingsUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class RelaySettingsResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    port: int
    download_limit: int
    upload_limit: int
    connections_limit: int
    torrent_connections_limit: int
    enable_upnp_and_natpmp: bool


class RelaySettingsUpdateRequest(RelaySettingsUpdate):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class NetworkLocalSettingsResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.LOCAL]
    host: str
    ip: str
    expires_at: datetime


class NetworkAutoSettingsResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.AUTO]
    host: str
    token: str
    email: str
    connection: NetworkConnectionEnum
    provider: str
    ip: str
    expires_at: datetime
    last_ip_sync_at: datetime


class NetworkManualSettingsResponse(NetworkManualSettings):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


NetworkSettingsResponse = Annotated[
    NetworkLocalSettingsResponse
    | NetworkAutoSettingsResponse
    | NetworkManualSettingsResponse,
    Field(discriminator="mode"),
]
