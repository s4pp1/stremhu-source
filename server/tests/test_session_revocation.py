import base64
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie

import pytest
from argon2 import PasswordHasher
from fastapi import HTTPException
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.config import config
from app.main import app
from app.modules.auth.dependencies import create_auth_service
from app.modules.roles.models import RoleModel
from app.modules.users.dependencies import create_users_service
from app.modules.users.models import UserModel
from app.modules.users.repository import UsersRepository
from app.modules.users.schemas.internal import UserUpdate

PASSWORD = "synthetic-session-password"
COOKIE = "stremhu.source"


@pytest.fixture
def session_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'sessions.db'}", connect_args={"check_same_thread": False}, hide_parameters=True)
    database.Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    with Session(engine) as db:
        db.add_all([RoleModel(id="admin", name="Fixture admin"), RoleModel(id="user", name="Fixture user")])
        db.flush()
        encoded = PasswordHasher().hash(PASSWORD)
        db.add_all([UserModel(id=name, username=name, role_id="admin", password_hash=encoded, api_key=f"synthetic-{name}") for name in ["one", "other"]])
        db.commit()
    try:
        yield engine
    finally:
        engine.dispose()


def client():
    return TestClient(app, base_url="https://fixture.invalid", raise_server_exceptions=False)


def login(username="one", password=PASSWORD):
    result = client()
    assert result.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200
    return result


def copy_session(original):
    duplicate = client()
    duplicate.cookies.update(original.cookies)
    return duplicate


def assert_session_deleted(response):
    deleted = SimpleCookie()
    deleted.load(response.headers["set-cookie"])
    assert parsedate_to_datetime(deleted[COOKIE]["expires"]) < datetime.now(timezone.utc)


@pytest.mark.parametrize("password", ["synthetic-new-password", None])
def test_own_password_revokes_both_sessions_but_preserves_other_user_and_api_key(session_engine, password):
    first, second, other = login(), login(), login("other")
    replay = copy_session(first)
    response = first.put("/api/me/", json={"password": password})
    assert response.status_code == 200
    assert "sessionEpoch" not in response.json() and "session_epoch" not in response.json()
    assert_session_deleted(response)
    for old in [first, second, replay]:
        assert old.get("/api/users/").status_code == 401
        assert old.get("/api/me/").json() is None
    assert other.get("/api/users/").status_code == 200
    with Session(session_engine) as db:
        assert create_auth_service(db).verify_api_key("synthetic-one").id == "one"
        user = db.get(UserModel, "one")
        assert user is not None and user.session_epoch == 1
        assert (user.password_hash is None) == (password is None)
    if password is not None:
        assert login(password=password).get("/api/me/").status_code == 200


def test_admin_password_change_revokes_only_target(session_engine):
    admin, target, replay = login("other"), login(), login()
    assert admin.put("/api/users/one", json={"password": "synthetic-new-password"}).status_code == 200
    assert target.get("/api/users/").status_code == 401
    assert replay.get("/api/me/").json() is None
    assert admin.get("/api/users/").status_code == 200


def test_profile_changes_keep_sessions_and_roles_are_fresh(session_engine):
    first, second = login(), login()
    assert first.put("/api/me/", json={"torrentSeed": 7}).status_code == 200
    assert second.get("/api/users/").status_code == 200
    with Session(session_engine) as db:
        user = db.get(UserModel, "one")
        assert user is not None
        assert user.session_epoch == 0
        user.role_id = "user"
        db.commit()
    assert second.get("/api/users/").status_code == 403
    assert second.get("/api/me/").json()["role"]["id"] == "user"


def test_local_logout_does_not_revoke_copied_cookie(session_engine):
    first = login()
    copied = copy_session(first)
    assert first.post("/api/auth/logout").status_code == 200
    assert first.get("/api/me/").json() is None
    assert copied.get("/api/users/").status_code == 200
    with Session(session_engine) as db:
        assert db.scalar(select(UserModel.session_epoch).where(UserModel.id == "one")) == 0


@pytest.mark.parametrize("epoch", [None, -1, 1, "0", False, 0.0])
@pytest.mark.parametrize("optional", [False, True])
def test_legacy_and_invalid_epochs_are_rejected_and_cleared(session_engine, epoch, optional):
    payload: dict[str, object] = {"user_id": "one"}
    if epoch is not None:
        payload["session_epoch"] = epoch
    token = TimestampSigner(str(config.session_secret)).sign(base64.b64encode(json.dumps(payload).encode())).decode()
    browser = client()
    browser.cookies.set(COOKIE, token)
    response = browser.get("/api/me/" if optional else "/api/users/")
    assert response.status_code == (200 if optional else 401)
    if optional:
        assert response.json() is None
    assert_session_deleted(response)


def test_password_and_epoch_rollback_together_on_commit_failure(session_engine):
    first, second = login(), login()

    def fail_commit(db):
        if db.get_bind() is session_engine:
            raise RuntimeError("synthetic commit failure")

    event.listen(Session, "before_commit", fail_commit)
    try:
        assert first.put("/api/me/", json={"password": "synthetic-new-password"}).status_code == 500
    finally:
        event.remove(Session, "before_commit", fail_commit)
    assert second.get("/api/users/").status_code == 200
    with Session(session_engine) as db:
        user = db.get(UserModel, "one")
        assert user is not None and user.session_epoch == 0
        assert user.password_hash is not None
        assert PasswordHasher().verify(user.password_hash, PASSWORD)


def test_explicit_password_rolls_back_with_later_validation_failure(session_engine):
    with Session(session_engine) as db:
        with pytest.raises(HTTPException) as error:
            create_users_service(db).update("one", UserUpdate(password="synthetic-new-password", smart_filter_grouping_preference_id="missing"))
        assert error.value.status_code == 400
        db.rollback()
    assert login().get("/api/users/").status_code == 200
    with Session(session_engine) as db:
        assert db.scalar(select(UserModel.session_epoch).where(UserModel.id == "one")) == 0


def test_sql_increment_preserves_both_revocations_with_stale_identity_maps(session_engine):
    # Both Sessions have the old value loaded. The second update must still add
    # to the committed value, rather than assigning its stale Python value + 1.
    with Session(session_engine, expire_on_commit=False) as first, Session(session_engine, expire_on_commit=False) as second:
        a, b = first.get(UserModel, "one"), second.get(UserModel, "one")
        assert a is not None and b is not None
        assert a.session_epoch == b.session_epoch == 0
        first.commit()
        second.commit()
        UsersRepository(first).bump_session_epoch("one")
        first.commit()
        assert b.session_epoch == 0
        UsersRepository(second).bump_session_epoch("one")
        second.commit()
    with Session(session_engine) as db:
        assert db.scalar(select(UserModel.session_epoch).where(UserModel.id == "one")) == 2


def test_login_replaces_all_previous_session_fields(session_engine):
    browser = login()
    payload = {"user_id":"other", "session_epoch":0, "obsolete":"synthetic previous session data"}
    signer = TimestampSigner(str(config.session_secret))
    browser.cookies.clear()
    browser.cookies.set(COOKIE, signer.sign(base64.b64encode(json.dumps(payload).encode())).decode())
    assert browser.post("/api/auth/login", json={"username":"one", "password":PASSWORD}).status_code == 200
    issued = browser.cookies.get(COOKIE, domain="fixture.invalid", path="/")
    assert issued is not None
    assert json.loads(base64.b64decode(signer.unsign(issued))) == {"user_id":"one", "session_epoch":0}
