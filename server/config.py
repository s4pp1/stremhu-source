import ipaddress
import os
import sys
from enum import Enum
from pathlib import Path

import platformdirs
from pydantic import (
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

from server.common.validators import validate_domain


class NodeEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"


def is_running_tests() -> bool:
    return "pytest" in sys.modules or any("pytest" in a for a in sys.argv)


def get_default_system_dir() -> Path:
    if is_running_tests():
        return Path("/tmp/stremhu_test")
    if Path("/data").exists():
        return Path("/data")
    return Path(platformdirs.user_data_dir("stremhu", "stremhu"))


def get_default_client_path() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and (Path(meipass) / "client").exists():
            return Path(meipass) / "client"
    for p in [Path("server/client"), Path("client/dist"), Path("/app/client")]:
        if p.exists():
            return p.resolve()
    return Path("client/dist")


def get_default_downloads_dir() -> Path:
    if Path("/downloads").exists():
        return Path("/downloads")
    try:
        return Path(platformdirs.user_downloads_dir())
    except Exception:
        return Path.home() / "Downloads"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        cli_parse_args=True,
        cli_kebab_case=True,
        cli_ignore_unknown_args=True,
        cli_implicit_flags=True,
    )

    node_env: NodeEnv = NodeEnv.PROD
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar torrentoldalakra építve."
    is_docker: bool = False
    host_ip: str = ""
    reload: bool = False
    reverse_proxy_domain: str | None = Field(
        default=None,
    )

    port: int | None = Field(
        default=None,
    )

    system_dir: Path = Field(
        default_factory=get_default_system_dir,
    )

    default_downloads_dir: Path | None = Field(
        default_factory=get_default_downloads_dir,
    )
    downloads_dir: Path | None = Field(
        default=None,
    )

    client_path: Path = Field(
        default_factory=get_default_client_path,
    )

    openapi_dir: Path | None = Field(
        default=None,
    )

    acme_directory_url: str = "https://acme-v02.api.letsencrypt.org/directory"

    port_override: bool = False

    @property
    def is_port_overridden(self) -> bool:
        if self.port_override:
            return True
        return any(a.startswith("--port") for a in sys.argv) or "PORT" in os.environ

    @property
    def libtorrent_port(self) -> int:
        return 6881

    @property
    def database_dir(self) -> Path:
        return self.system_dir / "database"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_dir}/app.db"

    @property
    def certificates_dir(self) -> Path:
        return self.system_dir / "certificates"

    @model_validator(mode="after")
    def validate_host_ip_and_domain(self) -> "Config":
        if is_running_tests() and not self.reverse_proxy_domain and not self.host_ip:
            self.host_ip = "192.168.1.100"
            return self
        if not self.reverse_proxy_domain and not self.host_ip:
            raise ValueError(
                "A `HOST_IP` megadása kötelező, ha a `REVERSE_PROXY_DOMAIN` nincs beállítva!"
            )

        if self.host_ip:
            try:
                ip = ipaddress.ip_address(self.host_ip)
            except ValueError:
                raise ValueError(
                    f"A megadott `HOST_IP` ({self.host_ip}) formátuma érvénytelen! Kérlek érvényes IPv4 címet adj meg!"
                )

            if ip.is_loopback:
                raise ValueError(
                    f"A megadott `HOST_IP` ({self.host_ip}) nem lehet a localhost!"
                )

        return self

    @field_validator("reverse_proxy_domain")
    @classmethod
    def validate_reverse_proxy_domain(cls, value: str | None) -> str | None:
        if value is None:
            return value

        return validate_domain(value)


try:
    config = Config()
except ValidationError as e:
    console = Console()
    console.print(
        "\n[bold red]‼️  Konfigurációs hiba történt az indítás során:[/bold red]\n"
    )
    for error in e.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]

        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]

        if field_path:
            console.print(f"  [bold yellow]- {field_path}:[/bold yellow] {msg}")
        else:
            console.print(f"  [bold yellow]-[/bold yellow] {msg}")
    console.print(
        "\n[bold]Kérlek javítsd a fenti hibákat, majd indítsd újra az alkalmazást![/bold]\n"
        "További információ: [blue]https://stremhu.app[/blue]\n"
    )
    sys.exit(1)


def show_internal_routes() -> bool:
    return config.node_env == NodeEnv.DEV


def is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False
