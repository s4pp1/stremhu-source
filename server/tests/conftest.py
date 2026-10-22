import importlib

from server.boot.setup import (
    run_migrations,
    setup_system_dir,
)
from server.common.session import ensure_session_secret


def pytest_configure(config):
    _ = config
    importlib.import_module("server.common.database")
    setup_system_dir()
    ensure_session_secret()
    run_migrations()
