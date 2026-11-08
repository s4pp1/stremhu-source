import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from alembic import command, op
from app.common import database

OLD = "54a9d30f7c82"
NEW = "6f0d92b1c843"


@pytest.fixture
def epoch_migration(tmp_path, monkeypatch):
    location = tmp_path / "epoch.db"
    engine = create_engine(f"sqlite:///{location}", hide_parameters=True)
    monkeypatch.setattr(database, "engine", engine)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.attributes["configure_logger"] = False
    try:
        yield engine, config, location
    finally:
        engine.dispose()


def fingerprint(engine):
    with engine.connect() as connection:
        rows = list(map(list, connection.execute(text("SELECT id,username,password_hash,api_key,role_id FROM users ORDER BY id"))))
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def test_additive_epoch_upgrade_backup_downgrade_and_reupgrade(epoch_migration, tmp_path):
    engine, config, location = epoch_migration
    # The history stays linear and contains the epoch revision; later additive revisions may follow it.
    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1
    assert NEW in {revision.revision for revision in script.walk_revisions()}
    command.upgrade(config, OLD)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO roles (id,name) VALUES ('user','Fixture')"))
        connection.execute(text("INSERT INTO users (id,username,api_key,password_hash,role_id,enable_smart_filter) VALUES ('fixture','fixture','synthetic-key','synthetic-hash','user',0)"))
        connection.execute(text("INSERT INTO settings (key,value) VALUES ('auth_bootstrap_complete','{}')"))
    before = fingerprint(engine)
    backup = tmp_path / "before-epoch.db"
    with sqlite3.connect(location) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    command.upgrade(config, NEW)
    columns = {column["name"]: column for column in inspect(engine).get_columns("users")}
    assert not columns["session_epoch"]["nullable"]
    assert fingerprint(engine) == before
    with engine.begin() as connection:
        assert connection.execute(text("SELECT session_epoch FROM users")).scalar_one() == 0
        connection.execute(text("UPDATE users SET session_epoch=2"))
        assert connection.execute(text("SELECT value FROM settings WHERE key='auth_bootstrap_complete'")).scalar_one() == "{}"
    with sqlite3.connect(backup) as saved:
        assert "session_epoch" not in {column[1] for column in saved.execute("PRAGMA table_info(users)")}
    command.downgrade(config, OLD)
    assert fingerprint(engine) == before
    assert "session_epoch" not in {column["name"] for column in inspect(engine).get_columns("users")}
    command.upgrade(config, NEW)
    assert fingerprint(engine) == before
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == (NEW,)
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert connection.execute(text("SELECT session_epoch FROM users")).scalar_one() == 0


def test_failed_epoch_upgrade_keeps_previous_head_and_foreign_keys(epoch_migration, monkeypatch):
    engine, config, _ = epoch_migration
    command.upgrade(config, OLD)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic add-column failure")

    monkeypatch.setattr(op, "add_column", fail)
    with pytest.raises(RuntimeError):
        command.upgrade(config, NEW)
    assert "session_epoch" not in {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == (OLD,)
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
