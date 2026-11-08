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

from app.common.validators import normalize_browser_origin, validate_domain


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
    session_allowed_origins: list[str] = Field(default_factory=list, repr=False)
    host_ip: str = Field(
        default="",
    )

    reverse_proxy_domain: str | None = None
    tmdb_api_key: str | None = None

    port: int = 7070
    relay_piece_timeout_seconds: float = Field(default=120.0, gt=0)
    relay_read_timeout_seconds: float = Field(default=15.0, gt=0)
    # Felirat: ASS->VTT konverzióra és memóriába gyűjtésre engedett max. forrásméret
    subtitle_max_source_bytes: int = Field(default=8 * 1024 * 1024, gt=0)
    # Feliratcache összesített bájtkerete (folyamaton belüli memória)
    subtitle_cache_max_bytes: int = Field(default=32 * 1024 * 1024, gt=0)
    # Indexerről letöltött .torrent dekódolt törzsének felső határa.
    # 48 MiB: a G15-ben natívan elfogadott legnagyobb metaadat (41,9 MB) felett;
    # felhasználói döntés 2026-11-07 (CR15a).
    indexer_torrent_max_bytes: int = Field(default=48 * 1024 * 1024, gt=0)
    # CR15/c (27) forráskeresési keret. Felhasználói UX/SLO-döntés 2026-11-07 (burst27-v3 után):
    # 12 egyidejű egyedi keresés, 15 s teljes határidő, 1 GiB-os konténer.
    source_search_max_parallel: int = Field(default=12, ge=1)
    source_search_deadline_seconds: float = Field(default=15.0, gt=0)
    # Az 1 GiB-os keretből levezetve (burst27-v3 és a kapu előtti diagnosztika): egy mentési köteg
    # legfeljebb 16 MiB nyers .torrent (a feldolgozás ~4x átmeneti memóriát visz), a letöltött,
    # még nem mentett bájtok folyamatszinten legfeljebb 32 MiB-ig indítanak új letöltést.
    # Diagnosztika (nem kapuadat): nehéz N=4 anon csúcs 64/32 MiB-tal +745, 32/16 MiB-tal +497 MiB.
    source_search_batch_max_bytes: int = Field(default=16 * 1024 * 1024, gt=0)
    source_search_pending_max_bytes: int = Field(default=32 * 1024 * 1024, gt=0)
    # Indexerenként egyszerre beengedett letöltés: az adapterek alapértelmezett 5-ös szemaforja.
    source_search_downloads_per_indexer: int = Field(default=5, ge=1)
    # Feldolgozott TorrentInfo-gyorsítótár fájlbejegyzés-kerete (~1,3 KiB/fájl, ~65 MiB).
    torrent_info_cache_max_files: int = Field(default=50_000, gt=0)

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

    @field_validator("session_allowed_origins")
    @classmethod
    def validate_session_allowed_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            if normalize_browser_origin(value)[0] != "https":
                raise ValueError("Csak explicit HTTPS böngésző-origin engedélyezhető.")
        return values

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
                    "A megadott `HOST_IP` formátuma érvénytelen! Kérlek érvényes IPv4 címet adj meg!"
                )

            if ip.is_loopback:
                raise ValueError(
                    "A megadott `HOST_IP` nem lehet a localhost!"
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
