"""A StremHU kiszolgáló (server) környezeti és CLI beállításai."""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from core.config import Config


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        extra="ignore",
    )

    client_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CLIENT_DIR", "STREMHU_CLIENT_DIR", "client_dir"),
        description="A webes kliens mappa elérési útja",
    )
    host_ip: str | None = Field(
        default=None,
        validation_alias=AliasChoices("HOST_IP", "host_ip"),
        description="A kiszolgáló IP címe",
    )
    data_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATA_DIR", "STREMHU_DATA_DIR", "data_dir"),
        description="Az adatbázis és adatok mappája",
    )
    downloads_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DOWNLOADS_DIR", "DOWNLOADS_DIR_OVERRIDE", "downloads_dir"
        ),
        description="A letöltések mappája",
    )
    port: int | None = Field(
        default=None,
        validation_alias=AliasChoices("PORT", "STREMHU_PORT", "port"),
        description="A kiszolgáló portja",
    )
    domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REVERSE_PROXY_DOMAIN", "domain"),
        description="Reverse proxy domain név",
    )
    node_env: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NODE_ENV", "node_env"),
        description="Környezet (dev / prod)",
    )
    is_docker: bool = Field(
        default=False,
        validation_alias=AliasChoices("IS_DOCKER", "is_docker"),
        description="Docker környezetben fut-e",
    )

    def apply_to_config(self, target_config: "Config | None" = None) -> None:
        """Átviszi a szerver beállításait a megadott (vagy alapértelmezett) Core konfigurációra."""
        from core.config import NodeEnv, config as default_config

        cfg = target_config if target_config is not None else default_config

        if self.client_dir is not None:
            cfg.client_dir_override = self.client_dir
        if self.host_ip is not None:
            cfg.host_ip = self.host_ip
        if self.data_dir is not None:
            cfg.data_dir_override = self.data_dir
        if self.downloads_dir is not None:
            cfg.downloads_dir_override = self.downloads_dir
        if self.port is not None:
            cfg.port = self.port
            cfg.port_override = True
        if self.domain is not None:
            cfg.reverse_proxy_domain = self.domain
        if self.node_env is not None:
            try:
                cfg.node_env = NodeEnv(self.node_env.lower())
            except ValueError:
                pass
        if self.is_docker:
            cfg.is_docker = True


def apply_server_settings(
    settings: ServerSettings | None = None,
    target_config: "Config | None" = None,
) -> ServerSettings:
    """Kényelmi függvény a ServerSettings példányosításához és érvényesítéséhez a Core konfigurációra."""
    if settings is None:
        settings = ServerSettings()
    settings.apply_to_config(target_config=target_config)
    return settings


def parse_args() -> ServerSettings:
    return ServerSettings()
