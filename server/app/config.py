import ipaddress
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.validators import validate_domain


class NodeEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent / ".env",
            Path.cwd() / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    node_env: NodeEnv = NodeEnv.PROD
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar torrentoldalakra építve."
    session_secret: str = "stremhu-source"
    host_ip: str = Field(
        default="",
        min_length=1,
    )

    reverse_proxy_domain: str | None = None

    port: int = 7070

    @property
    def libtorrent_port(self) -> int:
        return 6881

    @property
    def root_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def base_data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def openapi_dir(self) -> Path:
        return self.root_dir / "openapi"

    @property
    def client_path(self) -> Path:
        return self.root_dir / "client"

    @property
    def downloads_dir(self) -> Path:
        return self.base_data_dir / "downloads"

    @property
    def system_dir(self) -> Path:
        return self.base_data_dir / "system"

    @property
    def database_dir(self) -> Path:
        return self.system_dir / "database"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_dir}/app.db"

    @property
    def certificates_dir(self) -> Path:
        return self.system_dir / "certificates"

    acme_directory_url: str = "https://acme-v02.api.letsencrypt.org/directory"

    @field_validator("host_ip")
    @classmethod
    def validate_host_ip(cls, value: str) -> str:
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise ValueError(
                f"🚨 Hiba: A megadott HOST_IP ({value}) formátuma érvénytelen! Kérlek érvényes IPv4 címet adj meg!"
            )

        if value == "127.0.0.1":
            raise ValueError(
                f"🚨 Hiba: A megadott HOST_IP ({value}) nem lehet a localhost!"
            )

        return value

    @field_validator("reverse_proxy_domain")
    @classmethod
    def validate_reverse_proxy_domain(cls, value: str | None) -> str | None:
        if value is None:
            return value

        return validate_domain(value)


config = Config()


def show_internal_routes() -> bool:
    return config.node_env == NodeEnv.DEV


def is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False
