import logging
import sys

from hypercorn.config import Config
from hypercorn.run import run
from rich.console import Console
from rich.panel import Panel

from core.boot.bootstrap import bootstrap_app
from core.boot.schemas import BootNetworkConfig
from core.common.logger import setup_logger
from core.config import NodeEnv, config
from core.modules.settings.enums import NetworkModeEnum

setup_logger()


def create_hypercorn_config(
    boot_config: BootNetworkConfig, use_reloader: bool
) -> Config:
    hypercorn_config = Config()
    hypercorn_config.application_path = "core.main:app"
    hypercorn_config.bind = [f"0.0.0.0:{boot_config.port}"]
    hypercorn_config.use_reloader = use_reloader

    hypercorn_config.certfile = boot_config.cert_path
    hypercorn_config.keyfile = boot_config.key_path
    hypercorn_config.access_log_format = "%(m)s %(U)s%(q)s %(s)s %(L)s"
    hypercorn_config.accesslog = logging.getLogger("hypercorn.access")
    hypercorn_config.errorlog = logging.getLogger("hypercorn.error")

    return hypercorn_config


def start_server(
    boot_config: BootNetworkConfig | None = None,
    use_reloader: bool | None = None,
):
    is_dev = config.node_env == NodeEnv.DEV

    if boot_config is None:
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

    reloader_enabled = (
        use_reloader
        if use_reloader is not None
        else (is_dev and not getattr(sys, "frozen", False))
    )
    hypercorn_config = create_hypercorn_config(boot_config, reloader_enabled)

    run(hypercorn_config)


if __name__ == "__main__":
    boot_config = bootstrap_app()
    start_server(boot_config=boot_config)
