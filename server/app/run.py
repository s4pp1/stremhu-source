import logging

from hypercorn.config import Config
from hypercorn.run import run
from rich.console import Console
from rich.panel import Panel

from app.boot.network import ensure_network_settings
from app.boot.settings import ensure_default_settings
from app.boot.setup import run_migrations, setup_directories
from app.common.logger import setup_logger
from app.config import NodeEnv, config
from app.modules.settings.enums import NetworkModeEnum

setup_logger()


def start_server():
    is_dev = config.node_env == NodeEnv.DEV

    ensure_default_settings()
    boot_config = ensure_network_settings()

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

        url = f"{protocol}://{host}:{config.port}"

    if boot_config.network_settings.mode == NetworkModeEnum.AUTO:
        url = f"{protocol}://{boot_config.network_settings.host}:{config.port}"

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

    hypercorn_config = Config()
    hypercorn_config.application_path = "app.main:app"
    hypercorn_config.bind = [f"0.0.0.0:{config.port}"]
    hypercorn_config.use_reloader = is_dev

    hypercorn_config.certfile = boot_config.cert_path
    hypercorn_config.keyfile = boot_config.key_path
    hypercorn_config.access_log_format = "%(m)s %(U)s%(q)s %(s)s %(L)s"
    hypercorn_config.accesslog = logging.getLogger("hypercorn.access")
    hypercorn_config.errorlog = logging.getLogger("hypercorn.error")

    run(hypercorn_config)


if __name__ == "__main__":
    setup_directories()
    run_migrations()
    start_server()
