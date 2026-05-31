import ipaddress
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NodeEnv(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Settings
    node_env: NodeEnv = NodeEnv.PRODUCTION
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar trackeroldalakra építve."
    stremhu_catalog_url: str = "https://catalog.stremhu.app"
    session_secret: str = "stremhu-source"
    host_ip: str = Field(default="", min_length=1)

    @field_validator("host_ip")
    @classmethod
    def validate_host_ip(cls, value: str) -> str:
        try:
            ip_obj = ipaddress.ip_address(value)
        except ValueError:
            raise ValueError(
                f"🚨 Hiba: A megadott HOST_IP ({value}) formátuma érvénytelen! Kérlek érvényes IPv4 címet adj meg!"
            )

        if not ip_obj.is_private and value != "127.0.0.1":
            raise ValueError(
                f"🚨 Hiba: A megadott HOST_IP ({value}) nem egy helyi/privát IP-cím! A helyi eléréshez magánhálózati IP szükséges!"
            )

        return value

    # Server Ports
    port: int = 4300

    @property
    def libtorrent_port(self) -> int:
        return 6881

    @property
    def base_data_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "data"

    @property
    def downloads_dir(self) -> Path:
        return self.base_data_dir / "downloads"

    @property
    def system_dir(self) -> Path:
        return self.base_data_dir / "system"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.system_dir}/stremhu.db"

    @property
    def acme_directory_url(self) -> str:
        if self.node_env == NodeEnv.DEVELOPMENT:
            return "https://acme-staging-v02.api.letsencrypt.org/directory"
        return "https://acme-v02.api.letsencrypt.org/directory"

    @property
    def openapi_dir(self) -> Path:
        return Path(__file__).resolve().parent / "openapi"

    @property
    def client_path(self) -> Path:
        return Path(__file__).resolve().parent / "client"


config = Config()
