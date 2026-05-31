import sys
from pathlib import Path

from modules.settings.schemas import NetworkModeEnum

# Biztosítjuk, hogy a gyökér könyvtár benne legyen a Python keresési útvonalában
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from boot.network import ensure_network_settings
from boot.settings import ensure_default_settings
from boot.setup import run_migrations, setup_directories
from config import NodeEnv, config


def start_server():
    is_dev = config.node_env == NodeEnv.DEVELOPMENT

    ensure_default_settings()
    boot_config = ensure_network_settings()

    protocol = "https"

    global_url = None
    if boot_config.mode != NetworkModeEnum.LOCAL:
        protocol = "http"
        global_url = f"https://{boot_config.host}"

        if boot_config.cert_path and boot_config.key_path:
            protocol = "https"
            global_url = f"{protocol}://{boot_config.host}:{config.port}"

    local_url = f"{protocol}://{boot_config.host}:{config.port}"

    if global_url:
        print(
            f"⚠️  Amennyiben a domain-en nem éred el a szervert, használd a {local_url} címet."
        )
    else:
        print(
            f"⚠️  A szerver a {local_url} címen érhető el, de végezd el a DNS konfigurációt."
        )

    if global_url:
        print(f"🚀  A szerver a {global_url} címen érhető el.")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        reload=is_dev,
        ssl_certfile=boot_config.cert_path,
        ssl_keyfile=boot_config.key_path,
    )


if __name__ == "__main__":
    setup_directories()
    run_migrations()
    start_server()
