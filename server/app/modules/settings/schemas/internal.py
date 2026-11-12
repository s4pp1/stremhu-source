from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.config import config
from app.modules.settings.enums import (
    NetworkConnectionEnum,
    NetworkModeEnum,
    RelayEncryptionEnum,
    StorageCleanupThresholdUnitEnum,
    StorageCleanupTriggerEnum,
)


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


class StorageCleanupLastRun(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    at: int
    trigger: StorageCleanupTriggerEnum
    free_before: int
    free_after: int
    deleted_count: int
    threshold_reached: bool
    error: str | None = None


class SystemSettings(BaseModel):
    hit_and_run: bool = True
    keep_seed_seconds: int = 0
    cache_retention_seconds: int = 14 * 24 * 60 * 60  # 14 nap másodpercekben
    storage_cleanup_enabled: bool = False
    storage_cleanup_threshold_value: int = Field(default=10, ge=0)
    storage_cleanup_threshold_unit: StorageCleanupThresholdUnitEnum = (
        StorageCleanupThresholdUnitEnum.PERCENT
    )
    storage_cleanup_min_score: int = Field(default=60, ge=0, le=100)
    storage_cleanup_last_run: StorageCleanupLastRun | None = None


class SystemSettingsUpdate(BaseModel):
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
    cache_retention_seconds: int | None = None
    storage_cleanup_enabled: bool | None = None
    storage_cleanup_threshold_value: int | None = Field(default=None, ge=0)
    storage_cleanup_threshold_unit: StorageCleanupThresholdUnitEnum | None = None
    storage_cleanup_min_score: int | None = Field(default=None, ge=0, le=100)


class RelaySettings(BaseModel):
    port: int = Field(default_factory=lambda: config.libtorrent_port)
    download_limit: int = 0
    upload_limit: int = 0
    connections_limit: int = 200
    torrent_connections_limit: int = 20
    enable_upnp_and_natpmp: bool = False
    encryption: RelayEncryptionEnum = RelayEncryptionEnum.ENABLED
    enable_utp: bool = True


class RelaySettingsUpdate(BaseModel):
    port: int | None = None
    download_limit: int | None = None
    upload_limit: int | None = None
    connections_limit: int | None = None
    torrent_connections_limit: int | None = None
    enable_upnp_and_natpmp: bool | None = None
    encryption: RelayEncryptionEnum | None = None
    enable_utp: bool | None = None
