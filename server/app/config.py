import contextlib
import ipaddress
import os
import secrets
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

from app.common.validators import validate_domain


class NodeEnv(str, Enum):
    DEV = "dev"
    PROD = "prod"


PUBLIC_DEFAULT_SESSION_SECRET = "stremhu-source"
MIN_SESSION_SECRET_LENGTH = 32
SESSION_SECRET_FILENAME = "session_secret"


_NOTICE_ENV = "STREMHU_SESSION_SECRET_NOTICES"


def _notice(message: str) -> None:
    Console(stderr=True).print(f"[yellow]{message}[/yellow]")


def _notice_once(key: str, message: str) -> None:
    # A konfigurációt a szülő és a Hypercorn-worker is betölti; a környezeti jelölőt a
    # később indított folyamat örökli, így a figyelmeztetés folyamatfánként egyszer jelenik meg.
    shown = {item for item in os.environ.get(_NOTICE_ENV, "").split(",") if item}
    if key in shown:
        return
    os.environ[_NOTICE_ENV] = ",".join(sorted(shown | {key}))
    _notice(message)


def load_or_create_session_secret(path: Path) -> str:
    """A tárolt aláírókulcs, első használatkor atomikusan (0600) létrehozva.

    Plug & play: friss telepítéshez nem kell SESSION_SECRET. A kulcs az adatbázis mellett,
    az adatkötetben él, így a munkamenetek és a stream-tokenek túlélik az újraindítást.
    Sérült (üres vagy túl rövid) fájlt soha nem ír felül csendben. Fájlrendszer-hiba
    (jogosultság, csak olvasható kötet) ValueError-ként jelenik meg, így az indulási
    konfigurációs hibaüzenet kezeli, nyers traceback nélkül.
    """
    try:
        return _load_or_create_session_secret(path)
    except OSError as error:
        raise ValueError(
            f"A SESSION_SECRET kulcsfájl ({path}) nem olvasható vagy nem hozható létre"
            f" ({type(error).__name__}). Ellenőrizd az adatkötet jogosultságait, vagy adj meg SESSION_SECRET-et."
        ) from None


def _load_or_create_session_secret(path: Path) -> str:
    for _ in range(2):
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            value = None
        if value is not None:
            if len(value) < MIN_SESSION_SECRET_LENGTH:
                raise ValueError(
                    f"A tárolt SESSION_SECRET fájl ({path}) sérült. Töröld, vagy adj meg SESSION_SECRET-et."
                )
            return value
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_urlsafe(48)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(secret)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)  # atomikus; ha más folyamat megelőzött, az ő kulcsa érvényes
            except FileExistsError:
                continue
            except OSError:
                # Hard link nélküli fájlrendszer (egyes hálózati kötetek): kizárólagos létrehozás.
                try:
                    final = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    continue
                with os.fdopen(final, "w", encoding="utf-8") as handle:
                    handle.write(secret)
                    handle.flush()
                    os.fsync(handle.fileno())
            _notice(f"SESSION_SECRET nincs megadva: erős kulcs generálva ({path}). Az adatkötetet tartsd meg.")
            return secret
        finally:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()
    raise ValueError(f"A SESSION_SECRET fájl ({path}) nem olvasható.")


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent / ".env",
            Path.cwd() / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    node_env: NodeEnv = NodeEnv.PROD
    version: str = "0.0.0"
    description: str = "Torrentalapú streaming magyar torrentoldalakra építve."
    # Üresen hagyva (plug & play) az első induláskor generált, az adatkötetben tárolt kulcs
    # érvényes (lásd resolve_generated_session_secret); explicit értéknek erősnek kell lennie.
    session_secret: str = Field(default="", repr=False)
    session_secret_file: Path | None = Field(default=None, repr=False)
    host_ip: str = Field(
        default="",
    )

    reverse_proxy_domain: str | None = None

    port: int = 7070

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: str) -> str:
        # Hiányzó, üres vagy a régi nyilvános alapérték: a model-validátor generált kulcsra cseréli.
        if value.strip() == PUBLIC_DEFAULT_SESSION_SECRET:
            _notice_once(
                "public-default",
                "A SESSION_SECRET a régi nyilvános alapérték; helyette a generált, tárolt kulcs érvényes.",
            )
            return ""
        if not value.strip():
            return ""
        # A szóközzel kitöltött rövid kulcs nem erős: a hosszt a tartalmon mérjük.
        if len(value.strip()) < MIN_SESSION_SECRET_LENGTH:
            raise ValueError(
                "A SESSION_SECRET legalább 32 karakteres, erős, egyedi aláírókulcs legyen,"
                " vagy hagyd üresen, és a program generál egyet."
            )
        return value

    @model_validator(mode="after")
    def resolve_generated_session_secret(self) -> "Config":
        if not self.session_secret:
            path = self.session_secret_file or self.system_dir / SESSION_SECRET_FILENAME
            self.session_secret = load_or_create_session_secret(path)
        return self

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

    @model_validator(mode="after")
    def validate_host_ip_and_domain(self) -> "Config":
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


def load_config(*, load_dotenv: bool | None = None, **values: Any) -> Config:
    """Load settings through an explicit, dotenv-free test boundary when requested."""
    if load_dotenv is None:
        load_dotenv = os.environ.get("STREMHU_LOAD_DOTENV", "true").lower() not in {
            "false",
            "0",
            "no",
        }
    if not load_dotenv:
        # Public BaseSettings argument, verified against the installed version.
        values["_env_file"] = None
    return Config(**values)


try:
    config = load_config()
except ValidationError as e:
    console = Console()
    console.print(
        "\n[bold red]‼️  Konfigurációs hiba történt az indítás során:[/bold red]\n"
    )
    for error in e.errors(include_input=False, include_context=False):
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
