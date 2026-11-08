import asyncio
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie

import pytest
from argon2 import PasswordHasher
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.common import database, session_origin
from app.common.validators import normalize_browser_origin
from app.config import config, load_config
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.enums import NetworkModeEnum
from app.modules.settings.models import SettingModel
from app.modules.settings.schemas.internal import NetworkManualSettings
from app.modules.stremio.cache import stream_cache_state
from app.modules.users.models import UserModel


def request(headers=(), method="POST"):
    return Request({"type":"http", "method":method, "scheme":"https", "path":"/api/auth/login", "query_string":b"", "headers":[(key.lower().encode(), value.encode()) for key, value in headers]})


@pytest.fixture
def origin_engine(tmp_path, monkeypatch):
    session_origin.clear_origin_cache()
    engine = create_engine(f"sqlite:///{tmp_path / 'origins.db'}", hide_parameters=True)
    database.Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(config, "reverse_proxy_domain", None)
    monkeypatch.setattr(config, "session_allowed_origins", [])
    with Session(engine) as db:
        db.add(SettingModel(key="network", value={"mode":"manual", "host":"canonical.fixture.invalid"}))
        db.commit()
    try:
        yield engine
    finally:
        session_origin.clear_origin_cache()
        engine.dispose()


@pytest.mark.parametrize("origin", ["https://canonical.fixture.invalid", "https://CANONICAL.fixture.invalid:443"])
def test_configured_origin_normalizes_host_and_default_port(origin_engine, origin):
    session_origin.require_browser_origin(request([("Origin", origin)]))


@pytest.mark.parametrize("origin", ["null", "https://foreign.fixture.invalid", "http://canonical.fixture.invalid", "https://canonical.fixture.invalid:444", "https://canonical.fixture.invalid/", "https://canonical.fixture.invalid?", "https://canonical.fixture.invalid#", "https://user@canonical.fixture.invalid", "https://canonical.fixture.invalid:0"])
def test_foreign_null_or_malformed_origin_is_denied_even_with_spoofed_headers(origin_engine, origin):
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin", origin), ("Host", "foreign.fixture.invalid"), ("X-Forwarded-Host", "foreign.fixture.invalid")]))
    assert error.value.status_code == 403


def test_duplicate_origins_and_cross_site_metadata_cannot_bypass_policy(origin_engine):
    for headers in [
        [("Origin","https://canonical.fixture.invalid"), ("Origin","https://foreign.fixture.invalid")],
        [("Sec-Fetch-Site","cross-site")],
        [("Origin","https://canonical.fixture.invalid"), ("Sec-Fetch-Site","cross-site")],
    ]:
        with pytest.raises(HTTPException) as error:
            session_origin.require_browser_origin(request(headers))
        assert error.value.status_code == 403


def test_native_and_safe_requests_do_not_open_a_database_session(origin_engine):
    statements = []
    event.listen(origin_engine, "before_cursor_execute", lambda *args:statements.append(True))
    session_origin.require_browser_origin(request())
    session_origin.require_browser_origin(request([("Sec-Fetch-Site","same-origin")]))
    session_origin.require_browser_origin(request([("Origin","null")], method="GET"))
    session_origin.require_browser_origin(request([("Origin","null")], method="OPTIONS"))
    assert statements == []


def test_reverse_proxy_and_explicit_alternate_origins_come_only_from_configuration(origin_engine, monkeypatch):
    monkeypatch.setattr(config, "reverse_proxy_domain", "proxy.fixture.invalid")
    monkeypatch.setattr(config, "session_allowed_origins", ["https://local.fixture.invalid:8443"])
    for origin in ["https://proxy.fixture.invalid", "https://local.fixture.invalid:8443"]:
        session_origin.require_browser_origin(request([("Origin",origin), ("Host","internal-backend.invalid"), ("X-Forwarded-Host","untrusted.fixture.invalid")]))
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert error.value.status_code == 403


def test_unavailable_policy_fails_closed_without_error_values(origin_engine, monkeypatch):
    marker = "synthetic-sensitive-origin-error"

    def fail():
        raise RuntimeError(marker)

    monkeypatch.setattr(session_origin, "_configured_origins", fail)
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert error.value.status_code == 503
    assert marker not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("origin", ["*", "https://*.fixture.invalid", "http://fixture.invalid", "https://synthetic-sensitive-user@fixture.invalid", "https://fixture.invalid/path", "https://fixture.invalid:0", "https://faß.fixture.invalid"])
def test_config_allowlist_requires_explicit_https_origins_and_hides_inputs(origin):
    with pytest.raises(ValidationError) as error:
        load_config(load_dotenv=False, host_ip="192.0.2.1", session_secret=secrets.token_urlsafe(48), session_allowed_origins=[origin])
    assert origin not in str(error.value)


def test_origin_parser_preserves_scheme_port_and_ipv6():
    assert normalize_browser_origin("https://[2001:db8::1]:8443") == ("https","2001:db8::1",8443)
    assert normalize_browser_origin("https://xn--fa-hia.fixture.invalid") == ("https","xn--fa-hia.fixture.invalid",443)
    with pytest.raises(ValueError):
        normalize_browser_origin("https://faß.fixture.invalid")


def test_real_signed_session_mutations_cookie_flags_and_error_cache_policy(origin_engine):
    with Session(origin_engine) as db:
        db.add(RoleModel(id="admin", name="Synthetic admin"))
        db.flush()
        db.add(UserModel(id="one", username="one", role_id="admin", password_hash=PasswordHasher().hash("synthetic-origin-password")))
        db.commit()
    browser = TestClient(app, base_url="https://canonical.fixture.invalid")
    headers = {"Origin":"https://canonical.fixture.invalid"}
    logged = browser.post("/api/auth/login", headers=headers, json={"username":"one", "password":"synthetic-origin-password"})
    assert logged.status_code == 200
    cookie = SimpleCookie()
    cookie.load(logged.headers["set-cookie"])
    assert cookie["stremhu.source"]["secure"]
    assert cookie["stremhu.source"]["httponly"]
    assert cookie["stremhu.source"]["samesite"].lower() == "lax"
    assert browser.put("/api/me/", headers=headers, json={"torrentSeed":7}).status_code == 200
    foreign = {"Origin":"https://foreign.fixture.invalid", "X-Forwarded-Host":"foreign.fixture.invalid"}
    for method, path, payload in [("PUT","/api/me/",{"torrentSeed":9}), ("PUT","/api/users/one",{"torrentSeed":9}), ("POST","/api/auth/pair/verify",{"userCode":"1234"}), ("POST","/api/auth/logout",{})]:
        response = browser.request(method, path, headers=foreign, json=payload)
        assert response.status_code == 403
        assert response.headers["Cache-Control"] == "no-store"
    assert browser.get("/api/me/").json()["torrentSeed"] == 7
    assert browser.post("/api/auth/logout", headers=headers).status_code == 200
    assert browser.get("/api/me/").json() is None


def test_register_checks_origin_before_expensive_hash_and_public_pair_init_stays_open(origin_engine, monkeypatch):
    def forbidden_hash(*args, **kwargs):
        pytest.fail("foreign-origin bootstrap reached password hashing")

    monkeypatch.setattr(PasswordHasher, "hash", forbidden_hash)
    native = TestClient(app, base_url="https://canonical.fixture.invalid")
    headers = {"Origin":"https://foreign.fixture.invalid"}
    response = native.post("/api/auth/register", headers=headers, json={"username":"one", "password":"synthetic-origin-password"})
    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"
    assert native.post("/api/auth/pair/init", headers=headers).status_code == 200


def test_warm_policy_reads_network_once_and_only_global_changes_expire_it(origin_engine):
    statements = []
    event.listen(origin_engine, "before_cursor_execute", lambda *args:statements.append(True))
    for _ in range(20):
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert len(statements) == 1
    stream_cache_state.invalidate_user("one")
    session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert len(statements) == 1
    stream_cache_state.invalidate_all()
    session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert len(statements) == 2


def test_real_network_commit_changes_origin_and_rollback_keeps_previous_policy(origin_engine):
    session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    with database.db_session() as db:
        create_settings_service(db).save_network(NetworkManualSettings(mode=NetworkModeEnum.MANUAL, host="new.fixture.invalid"))
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    session_origin.require_browser_origin(request([("Origin","https://new.fixture.invalid")]))
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert error.value.status_code == 403
    with pytest.raises(RuntimeError), database.db_session() as db:
        create_settings_service(db).save_network(NetworkManualSettings(mode=NetworkModeEnum.MANUAL, host="rolled-back.fixture.invalid"))
        raise RuntimeError("synthetic rollback")
    session_origin.require_browser_origin(request([("Origin","https://new.fixture.invalid")]))
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://rolled-back.fixture.invalid")]))
    assert error.value.status_code == 403


@pytest.mark.parametrize("change", ["commit", "startup-clear"])
def test_old_origin_load_cannot_poison_new_generation(origin_engine, monkeypatch, change):
    entered, release = threading.Event(), threading.Event()
    original = session_origin._configured_origins
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        result = original()
        if calls == 1:
            entered.set()
            assert release.wait(3)
        return result

    monkeypatch.setattr(session_origin, "_configured_origins", load)
    with ThreadPoolExecutor(max_workers=1) as executor:
        old = executor.submit(session_origin.require_browser_origin, request([("Origin","https://canonical.fixture.invalid")]))
        try:
            assert entered.wait(2)
            if change == "commit":
                with database.db_session() as db:
                    create_settings_service(db).save_network(NetworkManualSettings(mode=NetworkModeEnum.MANUAL, host="new.fixture.invalid"))
            else:
                with Session(origin_engine) as db:
                    row = db.get(SettingModel,"network")
                    assert row is not None
                    row.value = {"mode":"manual", "host":"new.fixture.invalid"}
                    db.commit()
                session_origin.clear_origin_cache()
            session_origin.require_browser_origin(request([("Origin","https://new.fixture.invalid")]))
        finally:
            release.set()
        old.result(timeout=2)
    session_origin.require_browser_origin(request([("Origin","https://new.fixture.invalid")]))
    assert calls == 2
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert error.value.status_code == 403


def test_invalidated_policy_failure_does_not_fall_back_to_stale_origin(origin_engine, monkeypatch):
    session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    stream_cache_state.invalidate_all()

    def fail():
        raise RuntimeError("synthetic unavailable policy")

    monkeypatch.setattr(session_origin, "_configured_origins", fail)
    with pytest.raises(HTTPException) as error:
        session_origin.require_browser_origin(request([("Origin","https://canonical.fixture.invalid")]))
    assert error.value.status_code == 503


@pytest.mark.anyio
async def test_async_dependency_warm_path_and_cancelled_cold_load_owner(origin_engine, monkeypatch):
    canonical = request([("Origin","https://canonical.fixture.invalid")])
    await session_origin.browser_origin_dependency(canonical)
    original_to_thread = asyncio.to_thread

    async def no_thread(*args, **kwargs):
        pytest.fail("warm origin lookup dispatched a worker")

    with monkeypatch.context() as patch:
        patch.setattr(asyncio, "to_thread", no_thread)
        await session_origin.browser_origin_dependency(canonical)
    session_origin.clear_origin_cache()
    entered, release = threading.Event(), threading.Event()
    original = session_origin._configured_origins

    def load():
        value = original()
        entered.set()
        assert release.wait(2)
        return value

    monkeypatch.setattr(session_origin, "_configured_origins", load)
    loading = asyncio.create_task(session_origin.browser_origin_dependency(canonical))
    assert await original_to_thread(entered.wait, 2)
    loading.cancel()
    await asyncio.sleep(0)
    try:
        assert not loading.done()
        heartbeat = asyncio.Event()
        asyncio.get_running_loop().call_soon(heartbeat.set)
        await asyncio.wait_for(heartbeat.wait(), 1)
        assert not loading.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await loading
