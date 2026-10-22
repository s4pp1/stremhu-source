import logging

from hypercorn.config import Config
from hypercorn.run import run as run_hypercorn
from rich.console import Console
from rich.panel import Panel

from server.boot.bootstrap import bootstrap_app
from server.boot.schemas import BootNetworkConfig
from server.common.logger import setup_logger
from server.config import config
from server.modules.settings.enums import NetworkModeEnum


def run() -> None:
    setup_logger()
    boot_config = bootstrap_app()

    console = Console()
    protocol = "https"

    url = None

    if boot_config.network_settings.mode == NetworkModeEnum.LOCAL:
        host = boot_config.network_settings.host

        if boot_config.network_settings.self_signed:
            console.print(
                "\n[bold yellow]⚠️ Hiba történt a helyi elérés beállításánál. A szerver self-signed tanúsítvánnyal érhető el, ami korlátozza a használhatóságát! Ellenőrizd az internetkapcsolatot és indítsd újra a szervert! ⚠️[/]"
            )
            host = boot_config.network_settings.ip

        url = f"{protocol}://{host}:{boot_config.port}"

    if boot_config.network_settings.mode == NetworkModeEnum.AUTO:
        url = f"{protocol}://{boot_config.network_settings.host}:{boot_config.port}"

    if boot_config.network_settings.mode == NetworkModeEnum.MANUAL:
        protocol = "https"
        url = f"{protocol}://{boot_config.network_settings.host}"

    console.print()
    console.print(
        Panel(
            f"🚀 A szerver a [bold cyan underline]{url}[/] címen érhető el! 🚀",
            border_style="bold green",
            expand=False,
        )
    )
    console.print()

    hypercorn_config = _create_hypercorn_config(boot_config, config.reload)

    run_hypercorn(hypercorn_config)


def _create_hypercorn_config(
    boot_config: BootNetworkConfig, use_reloader: bool
) -> Config:
    hypercorn_config = Config()
    hypercorn_config.application_path = "server.app:app"
    hypercorn_config.bind = [f"0.0.0.0:{boot_config.port}"]
    hypercorn_config.use_reloader = use_reloader

    hypercorn_config.certfile = boot_config.cert_path
    hypercorn_config.keyfile = boot_config.key_path
    hypercorn_config.access_log_format = "%(m)s %(U)s%(q)s %(s)s %(L)s"
    hypercorn_config.accesslog = logging.getLogger("hypercorn.access")
    hypercorn_config.errorlog = logging.getLogger("hypercorn.error")

    return hypercorn_config
