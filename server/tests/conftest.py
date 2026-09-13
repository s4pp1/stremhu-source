import importlib

import pytest


def pytest_configure(config):
    _ = config
    importlib.import_module("app.common.database")


@pytest.fixture
def db():
    # Az app.config már importáláskor validál és hibás beállításnál kilép,
    # ezért itt importálunk, nem modul szinten.
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session

    from app.common.database import Base

    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def disable_foreign_keys(dbapi_connection, *_):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
