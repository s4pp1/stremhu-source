import uvicorn
from rich.console import Console
from rich.panel import Panel

from app.boot.network import ensure_network_settings
from app.boot.settings import ensure_default_settings
from app.boot.setup import run_migrations, setup_directories
from app.config import NodeEnv, config
from app.modules.settings.enums import NetworkModeEnum


def start_server():
    is_dev = config.node_env == NodeEnv.DEV
    is_prod = config.node_env == NodeEnv.PROD

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
        protocol = "http"
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

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=is_dev,
        ssl_certfile=boot_config.cert_path,
        ssl_keyfile=boot_config.key_path,
        log_level="warning" if is_prod else "info",
    )


if __name__ == "__main__":
    setup_directories()
    run_migrations()
    start_server()
