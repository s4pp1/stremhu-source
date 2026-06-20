import importlib


def pytest_configure(config):
    _ = config
    importlib.import_module("app.common.database")
