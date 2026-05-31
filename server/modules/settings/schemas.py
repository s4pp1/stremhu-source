from enum import Enum
from typing import Annotated, Literal
from uuid import uuid4

from config import config
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class NetworkModeEnum(str, Enum):
    LOCAL = "local"
    AUTO = "auto"
    MANUAL = "manual"


class NetworkConnectionEnum(str, Enum):
    LOCAL = "local"
    PUBLIC = "public"


class NetworkLocalSettings(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.LOCAL] = NetworkModeEnum.LOCAL
    host: str
    ip: str
    fullchain: str
    privkey: str
    expires_at: int


class NetworkAutoSettings(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.AUTO] = NetworkModeEnum.AUTO
    host: str
    token: str
    email: str
    connection: NetworkConnectionEnum
    provider: str
    ip: str
    account_key: str
    fullchain: str
    privkey: str
    expires_at: int


class NetworkManualSettings(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    mode: Literal[NetworkModeEnum.MANUAL] = NetworkModeEnum.MANUAL
    host: str
    reverse_proxy: bool


NetworkSettings = Annotated[
    NetworkLocalSettings | NetworkAutoSettings | NetworkManualSettings,
    Field(discriminator="mode"),
]


class SystemSettings(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    instance_id: str = Field(
        default_factory=lambda: str(uuid4()),
    )
    hit_and_run: bool = True
    keep_seed_seconds: int = 0
    cache_retention_seconds: int = 14 * 24 * 60 * 60  # 14 nap másodpercekben
    catalog_token: str | None = None


class SystemSettingsSave(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
    cache_retention_seconds: int | None = None
    catalog_token: str | None = None


class RelaySettings(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    port: int = Field(default_factory=lambda: config.libtorrent_port)
    download_limit: int = 0
    upload_limit: int = 0
    connections_limit: int = 200
    torrent_connections_limit: int = 20
    enable_upnp_and_natpmp: bool = False


class RelaySettingsUpdate(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    port: int | None = None
    download_limit: int | None = None
    upload_limit: int | None = None
    connections_limit: int | None = None
    torrent_connections_limit: int | None = None
    enable_upnp_and_natpmp: bool | None = None
