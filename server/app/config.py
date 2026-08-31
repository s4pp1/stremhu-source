import ipaddress
import sys
from enum import Enum
from pathlib import Path

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

from app.common.validators import validate_domain

def get_env_paths() -> tuple[Path, ...]:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            bundle_dir = exe_dir.parent.parent.parent
            return (bundle_dir / ".env", exe_dir / ".env")
        return (exe_dir / ".env",)
    return (
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    )


class NodeEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_paths(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    node_env: NodeEnv = NodeEnv.PROD
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar torrentoldalakra építve."
    session_secret: str = "stremhu-source"
    host_ip: str = Field(
        default="",
    )

    reverse_proxy_domain: str | None = None

    port: int = 7070

    @property
    def libtorrent_port(self) -> int:
        return 6881

    @property
    def app_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent.parent

    @property
    def root_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent

    @property
    def base_data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def openapi_dir(self) -> Path:
        return self.root_dir / "openapi"

    @property
    def client_path(self) -> Path:
        return self.app_dir / "client"

    downloads_dir_override: str | None = None

    @property
    def downloads_dir(self) -> Path:
        if self.downloads_dir_override:
            return Path(self.downloads_dir_override)
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

    @model_validator(mode="after")
    def validate_host_ip_and_domain(self) -> "Config":
        if not self.reverse_proxy_domain and not self.host_ip:
            if getattr(sys, "frozen", False):
                self.host_ip = "127.0.0.1"
            else:
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

            if ip.is_loopback and not getattr(sys, "frozen", False):
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
