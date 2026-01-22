from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    lib_torrent_port: int = Field(6881)
    port: int = Field(4300)


config = Config()  # type: ignore[call-arg]
