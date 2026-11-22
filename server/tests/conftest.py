import importlib
import os
import secrets

# Must precede every app import, including pytest_configure's database import.
# Tests never use an install's dotenv or signing key.
os.environ["STREMHU_LOAD_DOTENV"] = "false"
os.environ["SESSION_SECRET"] = secrets.token_urlsafe(48)


def pytest_configure(config):
    _ = config
    importlib.import_module("app.common.database")
