import server.common.models  # noqa: F401
from server.boot.network import ensure_network_settings
from server.boot.schemas import BootNetworkConfig
from server.boot.settings import ensure_default_settings
from server.boot.setup import (
    run_migrations,
    setup_system_dir,
)


def bootstrap_app() -> BootNetworkConfig:
    setup_system_dir()
    run_migrations()
    ensure_default_settings()
    return ensure_network_settings()
