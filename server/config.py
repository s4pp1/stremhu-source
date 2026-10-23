import ipaddress
import sys
from pathlib import Path

from pydantic import (
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

from server.common.validators import validate_domain


def is_running_tests() -> bool:
    return "pytest" in sys.modules or any("pytest" in a for a in sys.argv)


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        cli_parse_args=True,
        cli_kebab_case=True,
        cli_ignore_unknown_args=True,
        cli_implicit_flags=True,
    )

    reload: bool = False
    is_dev: bool = False
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar torrentoldalakra építve."
    host_ip: str = ""
    reverse_proxy_domain: str | None = Field(
        default=None,
    )

    port: int = 7070

    system_dir: Path
    client_path: Path

    default_downloads_dir: Path | None = Field(
        default=None,
    )
    downloads_dir: Path | None = Field(
        default=None,
    )

    openapi_dir: Path | None = Field(
        default=None,
    )

    acme_directory_url: str = "https://acme-v02.api.letsencrypt.org/directory"

    @property
    def is_downloads_dir_overridden(self) -> bool:
        return self.downloads_dir is not None

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

    @model_validator(mode="before")
    @classmethod
    def set_test_defaults(cls, data: object) -> object:
        if is_running_tests() and isinstance(data, dict):
            data.setdefault("system_dir", Path("/tmp/stremhu_test"))
            data.setdefault("client_path", Path("client/dist"))
            if "default_downloads_dir" not in data and "downloads_dir" not in data:
                data.setdefault(
                    "default_downloads_dir", Path("/tmp/stremhu_test/downloads")
                )
        return data

    @model_validator(mode="after")
    def validate_downloads_dir(self) -> "Config":
        if self.default_downloads_dir is None and self.downloads_dir is None:
            raise ValueError(
                "A `DEFAULT_DOWNLOADS_DIR` vagy a `DOWNLOADS_DIR` megadása kötelező!"
            )
        return self

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
    return config.is_dev


def is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False
