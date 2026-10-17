import sys

import setproctitle
from core.boot.bootstrap import bootstrap_app
from core.common.logger import logger, setup_logger
from core.run import start_server

from server.settings import (
    ServerCliArgs,
    ServerSettings,
    apply_server_settings,
    get_server_env_files,
    parse_args,
)

try:
    setproctitle.setproctitle("StremHU Core")
except Exception:
    pass

setup_logger()


def main() -> None:
    apply_server_settings()

    try:
        boot_config = bootstrap_app()
        start_server(boot_config=boot_config)
    except Exception as e:
        logger.exception("Kritikus hiba a szerver indítása során.")
        print(f"Kritikus indítási hiba: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

__all__ = [
    "ServerCliArgs",
    "ServerSettings",
    "apply_server_settings",
    "get_server_env_files",
    "main",
    "parse_args",
]
