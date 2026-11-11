"""Disposable migration/foreign-key baseline, no application data volume."""

import json
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from app.common import database

with tempfile.TemporaryDirectory() as directory:
    engine = create_engine(f"sqlite:///{Path(directory) / 'migration.db'}", hide_parameters=True)
    database.engine = engine
    config = Config("/app/alembic.ini")
    config.set_main_option("script_location", "/app/alembic")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        result = dict(fixture="disposable-migration-preflight-v1", head=MigrationContext.configure(connection).get_current_heads(), foreign_keys=connection.exec_driver_sql("PRAGMA foreign_keys").scalar(), sqlite_version=connection.exec_driver_sql("SELECT sqlite_version()").scalar())
    engine.dispose()
    print(json.dumps(result))
