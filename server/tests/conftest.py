import importlib

import pytest

_monkeypatch = pytest.MonkeyPatch()


def pytest_configure(config):
    _ = config

    _monkeypatch.setenv("SESSION_SECRET", "teszt-session-secret")

    importlib.import_module("app.common.database")


def pytest_unconfigure(config):
    _ = config

    _monkeypatch.undo()
