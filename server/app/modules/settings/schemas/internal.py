from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.config import config
from app.modules.settings.enums import NetworkConnectionEnum, NetworkModeEnum


class NetworkLocalSettings(BaseModel):
    mode: Literal[NetworkModeEnum.LOCAL]
    host: str
    ip: str
    self_signed: bool
    fullchain: str
    privkey: str
    expires_at: int


class NetworkAutoSettings(BaseModel):
    mode: Literal[NetworkModeEnum.AUTO]
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
    last_ip_sync_at: int = 0


class NetworkManualSettings(BaseModel):
    mode: Literal[NetworkModeEnum.MANUAL]
    host: str


NetworkSettings = Annotated[
    NetworkLocalSettings | NetworkAutoSettings | NetworkManualSettings,
    Field(discriminator="mode"),
]


class SystemSettings(BaseModel):
    hit_and_run: bool = True
    keep_seed_seconds: int = 0
    cache_retention_seconds: int = 14 * 24 * 60 * 60  # 14 nap másodpercekben


class SystemSettingsUpdate(BaseModel):
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
    cache_retention_seconds: int | None = None


class RelaySettings(BaseModel):
    port: int = Field(default_factory=lambda: config.libtorrent_port)
    download_limit: int = 0
    upload_limit: int = 0
    connections_limit: int = 200
    torrent_connections_limit: int = 20
    enable_upnp_and_natpmp: bool = False


class RelaySettingsUpdate(BaseModel):
    port: int | None = None
    download_limit: int | None = None
    upload_limit: int | None = None
    connections_limit: int | None = None
    torrent_connections_limit: int | None = None
    enable_upnp_and_natpmp: bool | None = None
