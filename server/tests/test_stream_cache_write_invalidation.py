import asyncio
import threading
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import httpx
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.common import commit_actions, database
from app.common.commit_actions import mark_stream_cache_dirty
from app.common.database import Base
from app.main import app
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_accounts.schemas import (
    IndexerAccountCreate,
    IndexerAccountUpdate,
)
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.preferences.models import PreferenceModel
from app.modules.roles.models import RoleModel
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.enums import NetworkModeEnum
from app.modules.settings.schemas.internal import (
    NetworkManualSettings,
    SystemSettingsUpdate,
)
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.schemas import StremioStream
from app.modules.stremio.service import (
    StremioService,
    _stream_cache_state,
    invalidate_stream_cache,
)
from app.modules.system_preference_definitions.dependencies import (
    create_system_preference_definitions_service,
)
from app.modules.torrent_source_provider.service import TorrentSourceProviderService
from app.modules.users.dependencies import create_users_service
from app.modules.users.models import UserModel
from app.modules.users.schemas.internal import UserUpdate


def payload(name="fixture"):
    return [StremioStream(name=name, description="fixture", url="https://fixture.invalid/media")]


def get_user(db: Session, identity: str) -> UserModel:
    user = db.get(UserModel, identity)
    assert user is not None
    return user


@pytest.fixture
def fixture_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'cache-writes.db'}", connect_args={"check_same_thread": False}, hide_parameters=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    with Session(engine) as db:
        db.add_all([RoleModel(id="admin", name="Fixture admin"), RoleModel(id="user", name="Fixture user")])
        db.add_all([PreferenceModel(id="pref-one", name="One", description="Fixture", allow_best_torrent_grouping=True), PreferenceModel(id="pref-two", name="Two", description="Fixture", allow_best_torrent_grouping=True)])
        db.flush()
        db.add_all([MediaAttributeModel(id="attr-one", name="One", preference_id="pref-one"), MediaAttributeModel(id="attr-two", name="Two", preference_id="pref-one"), MediaAttributeModel(id="attr-three", name="Three", preference_id="pref-two")])
        db.add_all([UserModel(id="one", username="one", role_id="admin", api_key="fixture-one", password_hash=PasswordHasher().hash("fixture-password"), torrent_seed=0), UserModel(id="two", username="two", api_key="fixture-two", torrent_seed=2)])
        db.commit()
    invalidate_stream_cache()
    try:
        yield engine
    finally:
        invalidate_stream_cache()
        engine.dispose()


def publish_both_users():
    for identity in ["one", "two"]:
        assert _stream_cache_state.put_if_revision(identity, identity, _stream_cache_state.revision(identity), payload(identity))


def test_successful_outer_commit_invalidates_only_target_user(fixture_engine):
    publish_both_users()
    with database.db_session() as db:
        create_users_service(db).update("one", UserUpdate(torrent_seed=42))
        assert _stream_cache_state.get("one") is not None
    assert _stream_cache_state.get("one") is None
    assert _stream_cache_state.get("two") is not None
    with Session(fixture_engine) as db:
        assert get_user(db, "one").torrent_seed == 42


def test_outer_rollback_keeps_cache_and_database_unchanged(fixture_engine):
    publish_both_users()
    with pytest.raises(RuntimeError), database.db_session() as db:
        create_users_service(db).update("one", UserUpdate(torrent_seed=42))
        raise RuntimeError("fixture rollback")
    assert _stream_cache_state.get("one") is not None
    with Session(fixture_engine) as db:
        assert get_user(db, "one").torrent_seed == 0


@pytest.mark.parametrize("rollback_nested", [False, True])
def test_savepoint_actions_wait_for_outer_commit_and_rollback_restores_scope(fixture_engine, rollback_nested):
    publish_both_users()
    with database.db_session() as db:
        create_users_service(db).update("one", UserUpdate(torrent_seed=1))
        nested = db.begin_nested()
        create_users_service(db).update("two", UserUpdate(torrent_seed=3))
        if rollback_nested:
            nested.rollback()
        else:
            nested.commit()
        assert _stream_cache_state.get("one") is not None
        assert _stream_cache_state.get("two") is not None
    assert _stream_cache_state.get("one") is None
    assert (_stream_cache_state.get("two") is not None) == rollback_nested


def test_failed_commit_discards_queued_actions(fixture_engine, monkeypatch):
    publish_both_users()

    class FailingSession(Session):
        def commit(self):
            raise RuntimeError("fixture commit failure")

    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=fixture_engine, class_=FailingSession))
    with pytest.raises(RuntimeError), database.db_session() as db:
        create_users_service(db).update("one", UserUpdate(torrent_seed=42))
    assert _stream_cache_state.get("one") is not None
    with Session(fixture_engine) as db:
        assert get_user(db, "one").torrent_seed == 0


def test_post_commit_invalidation_failure_uses_safe_global_fallback(fixture_engine, monkeypatch, caplog):
    publish_both_users()
    original = commit_actions._invalidate_scope

    def fail_user_scope(scope):
        if scope is not None:
            raise RuntimeError("synthetic-private-error-marker")
        original(scope)

    monkeypatch.setattr(commit_actions, "_invalidate_scope", fail_user_scope)
    with database.db_session() as db:
        create_users_service(db).update("one", UserUpdate(torrent_seed=42))
    assert _stream_cache_state.get("one") is None
    assert _stream_cache_state.get("two") is None
    assert "synthetic-private-error-marker" not in caplog.text
    with Session(fixture_engine) as db:
        assert get_user(db, "one").torrent_seed == 42


def test_coalesced_global_scope_and_read_only_commit(fixture_engine):
    publish_both_users()
    with database.db_session() as db:
        mark_stream_cache_dirty(db, "one")
        mark_stream_cache_dirty(db, "one")
        mark_stream_cache_dirty(db)
        mark_stream_cache_dirty(db, "two")
        assert _stream_cache_state.get("one") is not None
    assert _stream_cache_state.get("one") is None
    assert _stream_cache_state.get("two") is None
    publish_both_users()
    with database.db_session() as db:
        assert db.get(UserModel, "one") is not None
    assert _stream_cache_state.get("one") is not None


def test_indexer_create_update_delete_are_post_commit_global_changes(fixture_engine):
    with Session(fixture_engine) as db:
        db.add(IndexerDefinitionModel(id="fixture-indexer", name="Fixture", url="https://fixture.invalid", details_path="/details", preference_id="pref-one"))
        db.commit()
    for action in ["create", "update", "delete"]:
        publish_both_users()
        with database.db_session() as db:
            service = create_indexer_accounts_service(db)
            if action == "create":
                service.create(IndexerAccountCreate(indexer_id="fixture-indexer", username="fixture", password="fixture", download_full_torrent=False))
            elif action == "update":
                service.update("fixture-indexer", IndexerAccountUpdate(download_full_torrent=True))
            else:
                service.delete("fixture-indexer")
            assert _stream_cache_state.get("one") is not None
        assert _stream_cache_state.get("one") is None
        assert _stream_cache_state.get("two") is None


def test_user_key_rotation_and_delete_retire_the_target_scope(fixture_engine):
    publish_both_users()
    with database.db_session() as db:
        create_users_service(db).regenerate_api_key("one")
    assert _stream_cache_state.get("one") is None
    assert _stream_cache_state.get("two") is not None
    publish_both_users()
    with database.db_session() as db:
        current = db.get(UserModel, "one")
        assert current is not None
        create_users_service(db).delete("two", current)
    assert _stream_cache_state.get("two") is None
    assert _stream_cache_state.get("one") is not None


def test_actual_app_engine_hides_sensitive_sql_parameters():
    # The runner gives this engine a new disposable /app/data tmpfs, never a host DB.
    location = database.engine.url.database
    assert location is not None
    Path(location).parent.mkdir(parents=True, exist_ok=True)
    marker = "synthetic-db-credential-marker"
    with database.engine.connect() as connection:
        connection.exec_driver_sql("CREATE TEMP TABLE privacy_fixture (token TEXT UNIQUE)")
        try:
            connection.execute(text("INSERT INTO privacy_fixture VALUES (:token)"), {"token": marker})
            with pytest.raises(IntegrityError) as error:
                connection.execute(text("INSERT INTO privacy_fixture VALUES (:token)"), {"token": marker})
            assert marker not in "".join(traceback.format_exception(error.value))
        finally:
            connection.rollback()
            connection.exec_driver_sql("DROP TABLE IF EXISTS privacy_fixture")


def test_system_network_and_global_preference_writes_invalidate_all(fixture_engine):
    for network in [False, True]:
        publish_both_users()
        with database.db_session() as db:
            settings = create_settings_service(db)
            if network:
                settings.save_network(NetworkManualSettings(mode=NetworkModeEnum.MANUAL, host="fixture.invalid"))
            else:
                settings.save_system(SystemSettingsUpdate(keep_seed_seconds=42))
        assert _stream_cache_state.get("one") is None
        assert _stream_cache_state.get("two") is None
    identifiers = []
    for preference, attribute in [("pref-one", "attr-one"), ("pref-two", "attr-three")]:
        publish_both_users()
        with database.db_session() as db:
            service = create_system_preference_definitions_service(db)
            identifiers.append(service.create(preference, [attribute]).definition_id)
        assert _stream_cache_state.get("one") is None
        assert _stream_cache_state.get("two") is None
    for action in ["update", "reorder", "delete"]:
        publish_both_users()
        with database.db_session() as db:
            service = create_system_preference_definitions_service(db)
            if action == "update":
                service.update(identifiers[0], ["attr-two"])
            elif action == "reorder":
                service.reorder(["pref-two", "pref-one"])
            else:
                service.delete(identifiers[0])
        assert _stream_cache_state.get("one") is None
        assert _stream_cache_state.get("two") is None


def test_commit_and_invalidation_finish_before_success_body_is_visible(fixture_engine):
    body_sent, commit_started, release = threading.Event(), threading.Event(), threading.Event()

    class ObserveResponse:
        async def __call__(self, scope, receive, send):
            async def observed_send(message):
                if scope.get("path") == "/api/me/" and scope.get("method") == "PUT" and message["type"] == "http.response.body" and not message.get("more_body", False):
                    assert _stream_cache_state.get("one") is None
                    body_sent.set()
                await send(message)
            await app(scope, receive, observed_send)

    client = TestClient(ObserveResponse(), base_url="https://fixture.invalid")
    assert client.post("/api/auth/login", json={"username":"one", "password":"fixture-password"}).status_code == 200
    publish_both_users()

    def block_commit(connection):
        if not commit_started.is_set():
            commit_started.set()
            assert release.wait(3)

    event.listen(fixture_engine, "commit", block_commit)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(client.put, "/api/me/", json={"torrentSeed": 42})
            try:
                assert commit_started.wait(3)
                assert not body_sent.is_set()
            finally:
                release.set()
            assert result.result(timeout=3).status_code == 200
        assert body_sent.is_set()
    finally:
        release.set()
        event.remove(fixture_engine, "commit", block_commit)


@pytest.mark.anyio
@pytest.mark.parametrize("global_change", [False, True])
async def test_committed_global_change_fences_underlying_provider_join(global_change, fixture_engine):
    old_service = TorrentSourceProviderService(Mock(), Mock())
    new_service = TorrentSourceProviderService(Mock(), Mock())
    started, release = asyncio.Event(), asyncio.Event()
    calls = Counter()

    async def old_find(imdb_id):
        calls["old"] += 1
        started.set()
        await release.wait()
        return [], ["old-fixture"]

    async def new_find(imdb_id):
        calls["new"] += 1
        return [], ["new-fixture"]

    old_service._shared_search = lambda: cast(Any, SimpleNamespace(find_by_imdb_id=old_find))
    new_service._shared_search = lambda: cast(Any, SimpleNamespace(find_by_imdb_id=new_find))
    old = asyncio.create_task(old_service.find_by_imdb_id("tt1234567"))
    await started.wait()

    def mutate():
        with database.db_session() as db:
            if global_change:
                create_settings_service(db).save_system(SystemSettingsUpdate(keep_seed_seconds=43))
            else:
                create_users_service(db).update("one", UserUpdate(torrent_seed=43))

    try:
        await asyncio.to_thread(mutate)
        new = asyncio.create_task(new_service.find_by_imdb_id("tt1234567"))
        if global_change:
            assert await asyncio.wait_for(new, 1) == ([], ["new-fixture"])
            assert calls["new"] == 1
            release.set()
            assert await old == ([], ["old-fixture"])
        else:
            await asyncio.sleep(0)
            release.set()
            assert await new == ([], ["old-fixture"])
            assert calls["new"] == 0
    finally:
        release.set()
        await old


@pytest.mark.anyio
async def test_real_http_commit_fences_an_inflight_stream_cache_write(fixture_engine):
    service = StremioService(Mock(), Mock())
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def fetch(user, parsed_id):
        nonlocal calls
        calls += 1
        captured_seed = user.torrent_seed
        if calls == 1:
            started.set()
            await release.wait()
        return payload(f"seed:{captured_seed}")

    service._get_streams_uncached = fetch
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_stremio_service] = lambda: service
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://fixture.invalid") as client:
            assert (await client.post("/api/auth/login", json={"username":"one", "password":"fixture-password"})).status_code == 200
            path = "/api/fixture-one/stremio/stream/movie/tt1234567.json"
            old = asyncio.create_task(client.get(path))
            await started.wait()
            try:
                assert (await client.put("/api/me/", json={"torrentSeed":42})).status_code == 200
                fresh = await asyncio.wait_for(client.get(path), 1)
                assert fresh.json()["streams"][0]["name"] == "seed:42"
                release.set()
                assert (await old).json()["streams"][0]["name"] == "seed:0"
                assert (await client.get(path)).json()["streams"][0]["name"] == "seed:42"
                assert calls == 2
            finally:
                release.set()
                await old
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_http_commit_failure_cannot_emit_success_or_invalidate_cache(fixture_engine, monkeypatch):
    client = TestClient(app, raise_server_exceptions=False, base_url="https://fixture.invalid")
    assert client.post("/api/auth/login", json={"username":"one", "password":"fixture-password"}).status_code == 200
    publish_both_users()

    class FailingWriteCommit(Session):
        def commit(self):
            if commit_actions._DIRTY in self.info:
                raise RuntimeError("fixture failed write commit")
            return super().commit()

    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=fixture_engine, class_=FailingWriteCommit, autoflush=False))
    response = client.put("/api/me/", json={"torrentSeed":42})
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert _stream_cache_state.get("one") is not None
    with Session(fixture_engine) as db:
        assert get_user(db, "one").torrent_seed == 0


def test_real_user_preference_exclusion_grouping_write_endpoints_refresh_cache(fixture_engine):
    fetches = Counter()
    service = StremioService(Mock(), Mock())

    def load_policy(identity):
        with Session(fixture_engine) as db:
            user = get_user(db, identity)
            return repr((user.torrent_seed, user.smart_filter_grouping_preference_id, sorted(item.attribute_id for item in user.attribute_exclusions), [(item.definition.preference_id, item.order, [attribute.attribute_id for attribute in item.definition.definition_attributes]) for item in user.preference_definitions]))

    async def fetch(user, parsed_id):
        fetches[user.id] += 1
        return payload(await asyncio.to_thread(load_policy, user.id))

    service._get_streams_uncached = fetch
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_stremio_service] = lambda: service
    try:
        client = TestClient(app, base_url="https://fixture.invalid")
        assert client.post("/api/auth/login", json={"username": "one", "password": "fixture-password"}).status_code == 200
        first = "/api/fixture-one/stremio/stream/movie/tt1234567.json"
        other = "/api/fixture-two/stremio/stream/movie/tt1234567.json"
        old = client.get(first).json()["streams"][0]["name"]
        assert client.get(other).status_code == 200
        changes = [
            ("PUT", "/api/me/", {"torrentSeed": 5}),
            ("PUT", "/api/me/", {"smartFilterGroupingPreferenceId": "pref-one"}),
            ("POST", "/api/me/attributes/exclusions/", {"attributeId": "attr-one"}),
            ("DELETE", "/api/me/attributes/exclusions/attr-one", None),
            ("POST", "/api/me/preferences/definitions/", {"preferenceId": "pref-one", "attributeIds": ["attr-one"]}),
            ("PUT", "/api/me/preferences/definitions/pref-one", {"attributeIds": ["attr-two"]}),
            ("POST", "/api/me/preferences/definitions/", {"preferenceId": "pref-two", "attributeIds": ["attr-three"]}),
            ("PUT", "/api/me/preferences/definitions/reorder", {"preferenceIds": ["pref-two", "pref-one"]}),
            ("DELETE", "/api/me/preferences/definitions/pref-one", None),
        ]
        for method, path, body in changes:
            changed = client.request(method, path, json=body)
            assert changed.status_code in {200, 204}, changed.text
            new = client.get(first).json()["streams"][0]["name"]
            assert new != old
            old = new
            assert client.get(other).status_code == 200
            assert fetches["two"] == 1
        assert fetches["one"] == 1 + len(changes)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
