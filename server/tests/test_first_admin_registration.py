import concurrent.futures
import threading

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.users.models import UserModel

MARKER = "auth_bootstrap_complete"
PASSWORD = "synthetic-bootstrap-password"


@pytest.fixture
def bootstrap_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}", connect_args={"check_same_thread":False, "timeout":0.05}, hide_parameters=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    with Session(engine) as db:
        db.add_all([RoleModel(id="admin", name="Fixture admin"), RoleModel(id="user", name="Fixture user")])
        db.commit()
    try:
        yield engine
    finally:
        engine.dispose()


def register(username="fixture", *, peer="testclient"):
    return TestClient(app, raise_server_exceptions=False, base_url="https://fixture.invalid", client=(peer, 1234)).post("/api/auth/register", json={"username":username, "password":PASSWORD})


def assert_empty(engine):
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(UserModel)) == 0
        assert db.get(SettingModel, MARKER) is None


def test_ten_simultaneous_first_admin_calls_commit_exactly_one(bootstrap_engine, monkeypatch):
    barrier = threading.Barrier(10)
    original = PasswordHasher.hash

    def synchronized_hash(self, password, *args, **kwargs):
        barrier.wait(timeout=10)
        return original(self, password, *args, **kwargs)

    monkeypatch.setattr(PasswordHasher, "hash", synchronized_hash)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(lambda i:register(f"fixture-{i}"), range(10)))
    monkeypatch.setattr(PasswordHasher, "hash", original)
    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 1
    assert set(statuses) <= {201, 403, 503}
    for response in responses:
        assert response.headers["Cache-Control"] == "no-store"
        if response.status_code != 201:
            assert "set-cookie" not in response.headers
    with Session(bootstrap_engine) as db:
        assert db.scalar(select(func.count()).select_from(UserModel)) == 1
        assert db.get(SettingModel, MARKER) is not None
    assert register("retry", peer="192.0.2.1").status_code == 403


@pytest.mark.parametrize("failure", ["hash", "user-insert", "commit"])
def test_failed_bootstrap_leaves_no_marker_user_or_session(bootstrap_engine, monkeypatch, failure):
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic bootstrap failure")

    def before_flush(db, *args):
        if db.get_bind() is bootstrap_engine and any(isinstance(item, UserModel) for item in db.new):
            fail()

    if failure == "hash":
        monkeypatch.setattr(PasswordHasher, "hash", fail)
    elif failure == "commit":
        original = Session.commit

        def commit(db):
            if db.get_bind() is bootstrap_engine:
                fail()
            return original(db)

        monkeypatch.setattr(Session, "commit", commit)
    else:
        event.listen(Session, "before_flush", before_flush)
    try:
        response = register()
        assert response.status_code == 500
        assert "set-cookie" not in response.headers
        assert response.headers["Cache-Control"] == "no-store"
        assert_empty(bootstrap_engine)
    finally:
        if failure == "user-insert":
            event.remove(Session, "before_flush", before_flush)


def test_existing_user_without_marker_cannot_reopen_bootstrap(bootstrap_engine):
    with Session(bootstrap_engine) as db:
        db.add(UserModel(username="existing"))
        db.commit()
    assert register().status_code == 403
    with Session(bootstrap_engine) as db:
        assert db.scalar(select(func.count()).select_from(UserModel)) == 1
        assert db.get(SettingModel, MARKER) is None


def test_marker_survives_all_users_being_deleted(bootstrap_engine):
    first = register()
    assert first.status_code == 201
    with Session(bootstrap_engine) as db:
        db.query(UserModel).delete()
        db.commit()
    response = register("second")
    assert response.status_code == 403
    with Session(bootstrap_engine) as db:
        assert db.get(SettingModel, MARKER) is not None
        assert db.scalar(select(func.count()).select_from(UserModel)) == 0


def test_unrelated_integrity_failure_is_not_a_marker_conflict(bootstrap_engine):
    with Session(bootstrap_engine) as db:
        db.query(RoleModel).filter_by(id="admin").delete()
        db.commit()
    assert register().status_code == 500
    assert_empty(bootstrap_engine)


def test_committed_snapshot_materializes_nested_role_before_session_closes(bootstrap_engine):
    from app.modules.auth.bootstrap import BootstrapService
    from app.modules.users.schemas.api import UserResponse

    snapshot = BootstrapService().register_first_admin("fixture", PASSWORD)
    assert isinstance(snapshot.user, UserResponse)
    assert snapshot.user.role.id == "admin"
    assert "sessionEpoch" not in snapshot.user.model_dump(by_alias=True)
    with Session(bootstrap_engine) as db:
        assert db.get(UserModel, snapshot.user.id) is not None
        assert db.get(SettingModel, MARKER) is not None


def test_startup_backfill_closes_legacy_bootstrap_without_changing_user_data(bootstrap_engine):
    import hashlib

    from app.modules.auth.bootstrap import initialize_bootstrap_state

    initialize_bootstrap_state()
    assert_empty(bootstrap_engine)
    with Session(bootstrap_engine) as db:
        user = UserModel(username="legacy")
        db.add(user)
        db.commit()
        fingerprint = hashlib.sha256(user.api_key.encode()).digest()
        identity = user.id
    initialize_bootstrap_state()
    initialize_bootstrap_state()
    with Session(bootstrap_engine) as db:
        stored = db.get(UserModel, identity)
        assert stored is not None
        assert hashlib.sha256(stored.api_key.encode()).digest() == fingerprint
        assert db.get(SettingModel, MARKER) is not None
        db.query(UserModel).delete()
        db.commit()
    assert register().status_code == 403


def test_hash_holds_no_writer_lock_and_transaction_rechecks_user_count(bootstrap_engine, monkeypatch):
    started, release = threading.Event(), threading.Event()
    original = PasswordHasher.hash

    def paused_hash(self, password, *args, **kwargs):
        started.set()
        assert release.wait(2)
        return original(self, password, *args, **kwargs)

    monkeypatch.setattr(PasswordHasher, "hash", paused_hash)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        request = executor.submit(register)
        try:
            assert started.wait(2)
            # A separate connection can still commit while hashing is paused.
            with Session(bootstrap_engine) as db:
                db.add(UserModel(username="concurrent-legacy"))
                db.commit()
        finally:
            release.set()
        assert request.result(timeout=2).status_code == 403
    with Session(bootstrap_engine) as db:
        assert db.scalar(select(func.count()).select_from(UserModel)) == 1
        assert db.get(SettingModel, MARKER) is None


def test_writer_lock_timeout_is_controlled_and_no_session_is_issued(bootstrap_engine):
    with bootstrap_engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        response = register()
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "30"
        assert "set-cookie" not in response.headers
        connection.rollback()
    assert_empty(bootstrap_engine)


def test_successful_registration_issues_session_after_committed_snapshot(bootstrap_engine):
    client = TestClient(app, base_url="https://fixture.invalid")
    created = client.post("/api/auth/register", json={"username":"fixture", "password":PASSWORD})
    assert created.status_code == 201
    current = client.get("/api/me/")
    assert current.status_code == 200
    assert current.json()["id"] == created.json()["id"]
    assert "sessionEpoch" not in created.json()
