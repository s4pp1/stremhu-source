import datetime
from dataclasses import fields
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock

import pytest
from argon2 import PasswordHasher
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, update
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base, get_db
from app.main import app
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.relay.schemas import RelayTorrent
from app.modules.relay.service import RelayService
from app.modules.roles.models import RoleModel
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrents.dependencies import get_torrents_service
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.api import TorrentResponse
from app.modules.torrents.service import TorrentsService
from app.modules.users.models import UserModel

NOW = datetime.datetime(2026, 1, 1, 12)


def sorted_payload(items):
    return sorted(items, key=lambda item:(item["infoHash"], item["torrentId"], item["indexerDefinition"]["id"]))


@pytest.fixture
def list_fixture(tmp_path, monkeypatch):
    engines = []
    previous_overrides = app.dependency_overrides.copy()

    def create(count=20, indexers=5):
        engine = create_engine(f"sqlite:///{tmp_path / (str(len(engines))+'.db')}", connect_args={"check_same_thread":False}, hide_parameters=True)
        engines.append(engine)
        Base.metadata.create_all(engine)
        monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
        with Session(engine) as db:
            db.add(RoleModel(id="admin", name="Fixture admin"))
            db.flush()
            db.add(UserModel(username="admin", role_id="admin", password_hash=PasswordHasher().hash("fixture-password")))
            for i in range(indexers):
                identity = f"fixture-{i}"
                db.add(IndexerDefinitionModel(id=identity, name=identity, url="https://fixture.invalid", details_path="details", requires_full_download=i%2==0, supports_totp=i%2==1))
                db.flush()
                db.add(IndexerAccountModel(indexer_id=identity, username="synthetic", password="synthetic"))
            db.flush()
            db.execute(insert(TorrentFileModel), [dict(indexer_id=f"fixture-{i%indexers}", torrent_id=str(i), info_hash=f"{i+1:040x}", torrent_bytes=b"B"*65536, last_used_at=NOW, created_at=NOW) for i in range(count)])
            db.execute(insert(TorrentModel), [dict(indexer_id=f"fixture-{i%indexers}", torrent_id=str(i), info_hash=f"{i+1:040x}", resume_bytes=b"R"*65536, is_persisted=i%2==0, full_download=False, created_at=NOW, updated_at=NOW) for i in range(count)])
            db.commit()
        inventory = [RelayTorrent(info_hash=f"{i+1:040x}", name=f"fixture-{i}", download_speed=1, upload_speed=2, downloaded=3, uploaded=4, total=5, max_connections=50, connections=1) for i in range(count) if i%5 != 0]
        relay = Mock(spec=RelayService)
        relay.get_torrents.return_value = inventory

        def service(db: Annotated[Session, Depends(get_db, scope="function")]):
            return TorrentsService(TorrentRepository(db), Mock(), Mock(), Mock(), relay)

        app.dependency_overrides[get_torrents_service] = service
        return SimpleNamespace(engine=engine, relay=relay, inventory=inventory)

    try:
        yield create
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        for engine in engines:
            engine.dispose()


def legacy_payload(fixture):
    with Session(fixture.engine) as db:
        service = TorrentsService(TorrentRepository(db), Mock(), Mock(), Mock(), fixture.relay)
        return [TorrentResponse.from_torrent_with_relay(pair).model_dump(mode="json", by_alias=True) for pair in service.get_torrents()]


@pytest.mark.parametrize("count", [20, 100, 500])
@pytest.mark.parametrize("indexers", [1, 10])
def test_real_list_http_matches_legacy_with_one_projection_and_no_blobs(list_fixture, count, indexers):
    fixture = list_fixture(count, indexers)
    expected = legacy_payload(fixture)
    client = TestClient(app, base_url="https://fixture.invalid")
    assert client.post("/api/auth/login", json={"username":"admin", "password":"fixture-password"}).status_code == 200
    selects = []

    def trace(connection, cursor, statement, *args):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    fixture.relay.get_torrents.reset_mock()
    event.listen(fixture.engine, "before_cursor_execute", trace)
    response = client.get("/api/torrents/")
    assert response.status_code == 200
    assert sorted_payload(response.json()) == sorted_payload(expected)
    # Observe UI order on these fixtures without inventing a new sort policy.
    assert [item["torrentId"] for item in response.json()] == [item["torrentId"] for item in expected]
    assert len(selects) == 2  # existing auth SELECT + one complete list projection
    assert sum("FROM torrents" in statement for statement in selects) == 1
    assert all("torrent_bytes" not in statement and "resume_bytes" not in statement for statement in selects)
    fixture.relay.get_torrents.assert_called_once_with()


def test_records_and_nested_dto_are_usable_after_session_close(list_fixture):
    fixture = list_fixture()
    with Session(fixture.engine) as db:
        records = TorrentRepository(db).find_list_records()
    for record in records:
        assert all(not isinstance(getattr(record, field.name), (bytes, Base)) for field in fields(record))
    record = next(record for record in records if record.file_info_hash == fixture.inventory[0].info_hash)
    response = TorrentResponse.from_list_record(record, fixture.inventory[0])
    assert response.indexer_definition.id == record.indexer_id


def test_file_hash_selects_relay_but_model_hash_is_returned(list_fixture):
    fixture = list_fixture()
    with Session(fixture.engine) as db:
        db.execute(update(TorrentModel).where(TorrentModel.torrent_id=="1").values(info_hash="f"*40))
        db.commit()
    expected = legacy_payload(fixture)
    with Session(fixture.engine) as db:
        service = TorrentsService(TorrentRepository(db), Mock(), Mock(), Mock(), fixture.relay)
        result = [TorrentResponse.from_list_record(record, relay).model_dump(mode="json", by_alias=True) for record, relay in service.get_torrents_for_list()]
    assert sorted_payload(result) == sorted_payload(expected)
    assert any(item["infoHash"] == "f"*40 and item["name"] == "fixture-1" for item in result)


def test_legacy_missing_file_and_blank_file_hash_are_omitted(list_fixture):
    fixture = list_fixture()
    with fixture.engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(insert(TorrentModel), dict(indexer_id="fixture-0", torrent_id="missing", info_hash="f"*40, is_persisted=False, full_download=False, created_at=NOW, updated_at=NOW))
        connection.execute(update(TorrentFileModel).where(TorrentFileModel.torrent_id=="1").values(info_hash=""))
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    fixture.inventory.append(RelayTorrent(info_hash="", name="blank", download_speed=0, upload_speed=0, downloaded=0, uploaded=0, total=0, max_connections=50, connections=0))
    expected = legacy_payload(fixture)
    with Session(fixture.engine) as db:
        service = TorrentsService(TorrentRepository(db), Mock(), Mock(), Mock(), fixture.relay)
        result = [TorrentResponse.from_list_record(record, relay).model_dump(mode="json", by_alias=True) for record, relay in service.get_torrents_for_list()]
    assert sorted_payload(result) == sorted_payload(expected)


def test_general_find_and_restore_still_read_required_blobs(list_fixture):
    fixture = list_fixture(count=1, indexers=1)
    with Session(fixture.engine) as db:
        repository = TorrentRepository(db)
        torrents = repository.find()
        assert torrents[0].resume_bytes == b"R"*65536
        assert torrents[0].torrent_file.torrent_bytes == b"B"*65536
        service = TorrentsService(repository, Mock(), Mock(), Mock(), fixture.relay)
        service.restore_torrents()
    fixture.relay.add_torrent.assert_called_once_with(torrent_bytes=b"B"*65536, priority=0, resume_bytes=b"R"*65536)
