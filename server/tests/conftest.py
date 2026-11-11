import importlib
import os
import secrets

import pytest

# Must precede every app import, including pytest_configure's database import.
# Tests never use an install's dotenv or signing key.
os.environ["STREMHU_LOAD_DOTENV"] = "false"
os.environ["SESSION_SECRET"] = secrets.token_urlsafe(48)


def pytest_configure(config):
    _ = config
    importlib.import_module("app.common.database")


@pytest.fixture(autouse=True)
def isolated_auth_admission(monkeypatch):
    from app.common import auth_rate_limit

    monkeypatch.setattr(auth_rate_limit, "auth_rate_limiter", auth_rate_limit.AuthRateLimiter())


@pytest.fixture
def pairing_engine(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from app.common import database
    from app.common.database import Base
    from app.modules.roles.models import RoleModel
    from app.modules.users.models import UserModel

    engine = create_engine(f"sqlite:///{tmp_path / 'pairing.db'}", connect_args={"check_same_thread": False, "timeout": 0.05}, hide_parameters=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    with Session(engine) as db:
        db.add(RoleModel(id="user", name="Fixture user"))
        db.flush()
        db.add_all([UserModel(id="one", username="one", api_key="fixture-one"), UserModel(id="two", username="two", api_key="fixture-two")])
        db.commit()
    try:
        yield engine
    finally:
        engine.dispose()
