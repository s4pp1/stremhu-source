import hashlib
import json
import logging
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from alembic import command, op
from app.boot import setup
from app.common import database

OLD = "e72a1c3d4f5b"
NEW = "54a9d30f7c82"


@pytest.fixture
def migration_fixture(tmp_path, monkeypatch):
    location = tmp_path / "migration.db"
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


def head(engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_heads()


def fingerprint_users(engine):
    with engine.connect() as connection:
        rows = [list(row) for row in connection.execute(text("SELECT id, username, api_key FROM users ORDER BY id"))]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def seed_legacy_duplicates(engine):
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO roles (id,name) VALUES ('user','Fixture')"))
        connection.execute(text("INSERT INTO users (id,username,api_key,role_id,enable_smart_filter) VALUES (:id,:username,:api_key,'user',0)"), {"id":"fixture", "username":"fixture", "api_key":hashlib.sha256(b"fixture-only").hexdigest()})
        connection.execute(text("INSERT INTO pairings (id,user_code,device_code,status,expires_at,created_at) VALUES (:id,'1234','duplicate-fixture','pending','2099-01-01','2026-01-01')"), [{"id":"first"},{"id":"second"}])


def assert_fk_on(engine):
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_fresh_upgrade_and_single_head(migration_fixture):
    engine, config, _ = migration_fixture
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    command.upgrade(config, NEW)
    assert head(engine) == (NEW,)
    indexes = {index["name"]: index["unique"] for index in inspect(engine).get_indexes("pairings")}
    assert indexes["ix_pairings_user_code"]
    assert indexes["ix_pairings_device_code"]
    assert_fk_on(engine)


def test_existing_duplicates_backup_upgrade_downgrade_and_users_unchanged(migration_fixture, tmp_path):
    engine, config, location = migration_fixture
    command.upgrade(config, OLD)
    seed_legacy_duplicates(engine)
    before = fingerprint_users(engine)
    backup = tmp_path / "before.db"
    with sqlite3.connect(location) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    command.upgrade(config, NEW)
    assert fingerprint_users(engine) == before
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM pairings")).scalar() == 0
    with sqlite3.connect(backup) as saved:
        assert saved.execute("SELECT count(*) FROM pairings").fetchone()[0] == 2
    command.downgrade(config, OLD)
    assert head(engine) == (OLD,)
    assert fingerprint_users(engine) == before
    assert not any(index["unique"] for index in inspect(engine).get_indexes("pairings"))
    command.upgrade(config, NEW)
    assert fingerprint_users(engine) == before
    assert_fk_on(engine)


def test_failed_unique_index_upgrade_restores_rows_indexes_head_and_fk(migration_fixture, monkeypatch):
    engine, config, _ = migration_fixture
    command.upgrade(config, OLD)
    seed_legacy_duplicates(engine)
    before = fingerprint_users(engine)
    original = op.create_index
    calls = 0

    def fail_second_index(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("fixture index creation failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(op, "create_index", fail_second_index)
    with pytest.raises(RuntimeError):
        command.upgrade(config, NEW)
    assert head(engine) == (OLD,)
    assert fingerprint_users(engine) == before
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM pairings")).scalar() == 2
    indexes = inspect(engine).get_indexes("pairings")
    assert len(indexes) == 2 and not any(index["unique"] for index in indexes)
    assert_fk_on(engine)


def test_programmatic_boot_migration_preserves_safe_logging_handlers(migration_fixture):
    engine, config, _ = migration_fixture
    root = logging.getLogger()
    handlers = list(root.handlers)
    disabled = setup.logger.disabled
    setup.run_migrations()
    assert root.handlers == handlers
    assert setup.logger.disabled == disabled
    assert head(engine) == tuple(ScriptDirectory.from_config(config).get_heads())
    assert_fk_on(engine)
