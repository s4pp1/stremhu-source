import concurrent.futures
import hashlib
import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.common.database import Base, get_db
from app.config import load_config, load_or_create_session_secret
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.stream.schemas import StreamToken
from app.modules.stream.utils.stream_token import (
    generate_stream_token,
    parse_stream_token,
    serializer,
)
from app.modules.users.models import UserModel


@pytest.mark.parametrize("secret", ["short-marker", "x" * 31, "abc" + " " * 29])
def test_weak_explicit_signing_key_is_rejected_without_disclosure(monkeypatch, tmp_path, secret):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ValidationError) as error:
        load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret=secret,
                    session_secret_file=tmp_path / "session_secret")
    assert "session_secret" in str(error.value)
    assert secret not in str(error.value)
    assert not (tmp_path / "session_secret").exists()


@pytest.mark.parametrize("secret", [None, "", " " * 32, "stremhu-source"])
def test_missing_or_public_default_key_uses_one_persisted_generated_key(monkeypatch, tmp_path, secret):
    # Plug & play: a fresh install needs no SESSION_SECRET, and the public default is never used.
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    values = {} if secret is None else {"session_secret": secret}
    key_file = tmp_path / "system" / "session_secret"
    first = load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret_file=key_file, **values)
    restarted = load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret_file=key_file, **values)
    assert len(first.session_secret) >= 32
    assert first.session_secret != "stremhu-source"
    assert first.session_secret == restarted.session_secret == key_file.read_text(encoding="utf-8").strip()
    assert first.session_secret not in repr(first)
    if os.name == "posix":
        assert key_file.stat().st_mode & 0o777 == 0o600


def test_explicit_strong_key_wins_and_creates_no_key_file(monkeypatch, tmp_path):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    key = secrets.token_urlsafe(48)
    loaded = load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret=key,
                         session_secret_file=tmp_path / "session_secret")
    assert loaded.session_secret == key
    assert not (tmp_path / "session_secret").exists()


def test_corrupt_key_file_is_reported_and_never_overwritten(monkeypatch, tmp_path):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    key_file = tmp_path / "session_secret"
    key_file.write_text("short", encoding="utf-8")
    with pytest.raises(ValidationError) as error:
        load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret_file=key_file)
    assert "sérült" in str(error.value)
    assert key_file.read_text(encoding="utf-8") == "short"


def test_unusable_key_location_is_a_clear_configuration_error(monkeypatch, tmp_path):
    # A read-only or foreign-owned data volume must not crash the start with a raw traceback.
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    key_location = tmp_path / "session_secret"
    key_location.mkdir()  # reading a directory fails with an OSError on every platform
    with pytest.raises(ValidationError) as error:
        load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret_file=key_location)
    message = str(error.value)
    assert "session_secret" in message.lower()
    assert "nem olvasható vagy nem hozható létre" in message


def test_public_default_warning_is_printed_once_per_process_tree(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setenv("STREMHU_SESSION_SECRET_NOTICES", "")  # restored after the test
    key_file = tmp_path / "session_secret"
    for _ in range(3):
        load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret="stremhu-source",
                    session_secret_file=key_file)
    assert capsys.readouterr().err.count("régi nyilvános alapérték") == 1
    assert "public-default" in os.environ["STREMHU_SESSION_SECRET_NOTICES"]  # inherited by the worker


def test_concurrent_first_start_agrees_on_one_generated_key(tmp_path):
    key_file = tmp_path / "session_secret"
    barrier = threading.Barrier(8)

    def start() -> str:
        barrier.wait()
        return load_or_create_session_secret(key_file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(lambda _: start(), range(8)))
    assert len(set(keys)) == 1
    assert keys[0] == key_file.read_text(encoding="utf-8")
    assert [p.name for p in tmp_path.iterdir()] == ["session_secret"]  # no leftover temporary files


def test_dotenv_is_never_opened_in_isolated_loader(monkeypatch):
    original = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.name == ".env":
            pytest.fail("isolated configuration attempted dotenv access")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    key = secrets.token_urlsafe(48)
    first = load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret=key)
    second = load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret=key)
    assert first.session_secret == second.session_secret == key
    assert key not in repr(first)


def session_app(key):
    application = FastAPI()
    application.add_middleware(SessionMiddleware, secret_key=key)

    @application.post("/issue")
    def issue(request: Request):
        request.session["user_id"] = "fixture-user"
        return {}

    @application.get("/identity")
    def identity(request: Request):
        return {"user_id": request.session.get("user_id")}

    return application


def test_actual_session_middleware_survives_restart_and_rejects_other_key():
    key = secrets.token_urlsafe(48)
    issuing = TestClient(session_app(key))
    assert issuing.post("/issue").status_code == 200
    restarted = TestClient(session_app(key))
    restarted.cookies.update(issuing.cookies)
    assert restarted.get("/identity").json() == {"user_id": "fixture-user"}
    other = TestClient(session_app(secrets.token_urlsafe(48)))
    other.cookies.update(issuing.cookies)
    assert other.get("/identity").json() == {"user_id": None}


def test_stream_token_uses_configured_key_and_existing_salt():
    payload = StreamToken(indexer_id="fixture", torrent_id="1", file_index=0, playback_id="p")
    token = generate_stream_token(payload)
    assert parse_stream_token(token) == payload
    from app.config import config

    restarted = URLSafeSerializer(config.session_secret, salt="stream-token")
    assert restarted.loads(token) == payload.model_dump()
    foreign = URLSafeSerializer(secrets.token_urlsafe(48), salt="stream-token")
    with pytest.raises(BadSignature):
        foreign.loads(token)
    with pytest.raises(BadSignature):
        serializer.loads(foreign.dumps(payload.model_dump()))


def test_app_import_has_no_dotenv_fallback_with_missing_secret(tmp_path):
    # A tempting dotenv must not supply the key when dotenv loading is off: the app starts with
    # its own generated, persisted key instead (plug & play), never with the dotenv value.
    dotenv_key = secrets.token_urlsafe(48)
    (tmp_path / ".env").write_text("SESSION_SECRET=" + dotenv_key)
    key_file = tmp_path / "data" / "session_secret"
    environment = os.environ.copy()
    environment.pop("SESSION_SECRET", None)
    environment["STREMHU_LOAD_DOTENV"] = "false"
    environment["SESSION_SECRET_FILE"] = str(key_file)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-B", "-c",
         "import hashlib, app.config as c; print(hashlib.sha256(c.config.session_secret.encode()).hexdigest())"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-500:]
    loaded = result.stdout.strip().splitlines()[-1]
    stored = key_file.read_text(encoding="utf-8").strip()
    assert loaded == hashlib.sha256(stored.encode()).hexdigest()
    assert loaded != hashlib.sha256(dotenv_key.encode()).hexdigest()
    assert dotenv_key not in result.stdout + result.stderr


def test_real_login_and_session_with_disposable_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(32)
    with Session(engine) as db:
        db.add(RoleModel(id="user", name="Fixture"))
        db.flush()
        db.add(UserModel(username="fixture", password_hash=PasswordHasher().hash(password)))
        db.commit()

    def fixture_db():
        with Session(engine) as db:
            yield db

    old_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = fixture_db
    try:
        client = TestClient(app, base_url="https://fixture.invalid")
        assert client.get("/api/me/").json() is None
        response = client.post("/api/auth/login", json={"username": "fixture", "password": password})
        assert response.status_code == 200
        assert client.get("/api/me/").json()["username"] == "fixture"
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/me/").json() is None
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)
        engine.dispose()
