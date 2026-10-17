import importlib

from core.boot.setup import (
    ensure_session_secret,
    run_migrations,
    setup_system_dir,
)


def pytest_configure(config):
    _ = config
    importlib.import_module("core.common.database")
    setup_system_dir()
    ensure_session_secret()
    run_migrations()
