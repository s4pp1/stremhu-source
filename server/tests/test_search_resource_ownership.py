"""CR17/c–d regressions: a shared provider search owns its own resources.

A joiner receives the same Singleflight result as the owner request. The owner's
request Session commits (expire_on_commit) and closes when its response finishes,
or the owner is cancelled, while the shared task and the joiner continue. Real file
SQLite, real provider, repository and isolated file service; only the tracker
metadata is a gated synthetic double.
"""

import asyncio
import threading
from types import SimpleNamespace
from typing import Any, cast

import libtorrent
import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common import database
from app.common.database import Base
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import IndexerAccountRef
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.indexers.search import IndexerSearchService
from app.modules.kodi.schemas.api import KodiImdbStreamsResponse
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier
from app.modules.torrent_source_provider import service as providers
from app.modules.torrent_streams.schemas import TorrentStream

INDEXER_ID = "ownership-indexer"
TORRENT_ID = "ownership-torrent"
TORRENT_BYTES = libtorrent.bencode(
    {b"info": {b"name": b"ownership.mkv", b"piece length": 16384, b"pieces": b"\0" * 20, b"length": 1}}
)


@pytest.fixture
def file_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'ownership.db'}", connect_args={"check_same_thread": False}, hide_parameters=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    with session_factory() as db:
        definition = IndexerDefinitionModel(id=INDEXER_ID, name="Ownership Indexer", url="https://ownership.invalid", details_path="/")
        account = IndexerAccountModel(indexer_id=INDEXER_ID, username="fixture", password="fixture")
        account.indexer_definition = definition
        db.add_all([definition, account, TorrentFileModel(indexer_id=INDEXER_ID, torrent_id=TORRENT_ID, torrent_bytes=TORRENT_BYTES)])
        db.commit()
        stored = db.get(TorrentFileModel, (INDEXER_ID, TORRENT_ID))
        assert stored is not None
        expected_info_hash = stored.info_hash
    try:
        yield expected_info_hash
    finally:
        engine.dispose()


class _NoTouchFiles(IsolatedTorrentFilesService):
    # The row already exists, so no download/create path runs; the fire-and-forget
    # touch is covered by the lifespan drain tests.
    def touch(self, identifiers):
        return None


def _account_ref() -> IndexerAccountRef:
    # Like IndexerSearchService: its own short Session, never the request Session.
    with database.isolated_db_session() as db:
        return IndexerAccountRef.from_model(db.get_one(IndexerAccountModel, INDEXER_ID))


def _provider(indexer_method, metadata):
    return providers.TorrentSourceProviderService(
        indexers_service=cast(Any, SimpleNamespace(**{indexer_method: metadata})),
        isolated_torrent_files_service=_NoTouchFiles(),
    )


def _orm_instances(value, seen=None):
    """Every SQLAlchemy-mapped object reachable through pydantic fields, lists and tuples."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return []
    seen.add(id(value))
    if isinstance(value, Base):
        return [value]
    if isinstance(value, (list, tuple)):
        return [found for item in value for found in _orm_instances(item, seen)]
    if isinstance(value, BaseModel):
        return [found for name in type(value).model_fields for found in _orm_instances(getattr(value, name), seen)]
    return []


def test_search_service_reads_account_refs_in_its_own_session(file_db):
    search = IndexerSearchService(cast(Any, SimpleNamespace()))

    refs = search._find_account_refs()

    assert [ref.indexer_id for ref in refs] == [INDEXER_ID]
    assert search._get_account_ref(INDEXER_ID) == refs[0]
    assert not _orm_instances(refs)
    assert database.SessionLocal.kw["bind"].pool.checkedout() == 0



def test_shared_reads_open_one_extra_connection_at_a_time(file_db):
    # Without the limit, parallel shared searches saturated the QueuePool next to the
    # still-open request Sessions (cr17d-pool-diagnostic-v1).
    holding, release = threading.Event(), threading.Event()
    results = []

    def hold_slot():
        with database.shared_read_session():
            holding.set()
            release.wait(5)

    holder = threading.Thread(target=hold_slot)
    holder.start()
    assert holding.wait(5)
    reader = threading.Thread(
        target=lambda: results.append(
            IsolatedTorrentFilesService().find_snapshots([TorrentFileIdentifier(indexer_id=INDEXER_ID, torrent_id=TORRENT_ID)])
        )
    )
    reader.start()
    reader.join(0.3)
    assert reader.is_alive() and not results
    release.set()
    holder.join(5)
    reader.join(5)

    assert [snapshot.info_hash for snapshot in results[0]] == [file_db]
    assert database.SessionLocal.kw["bind"].pool.checkedout() == 0


def test_shared_read_fails_fast_when_nested_and_releases_on_error(file_db):
    with database.shared_read_session():
        with pytest.raises(RuntimeError, match="not reentrant"):
            with database.shared_read_session():
                pass
    with pytest.raises(ValueError):
        with database.shared_read_session():
            raise ValueError("read failed")

    # Both the nested refusal and the error path left the slot free.
    assert IndexerSearchService(cast(Any, SimpleNamespace()))._get_account_ref(INDEXER_ID).indexer_id == INDEXER_ID
    assert database.SessionLocal.kw["bind"].pool.checkedout() == 0

@pytest.mark.anyio
@pytest.mark.parametrize(
    ("indexer_method", "provider_method", "key"),
    [
        ("get_torrents_by_imdb_id", "find_by_imdb_id", "tt0000021"),
        ("get_torrents_by_torrent_id", "find_by_torrent_id", "ownership-direct"),
    ],
)
async def test_joiner_reads_shared_sources_after_owner_request_closed(file_db, indexer_method, provider_method, key):
    entered, release, owner_closed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    metadata_calls = 0

    async def gated_metadata(_):
        nonlocal metadata_calls
        metadata_calls += 1
        entered.set()
        await release.wait()
        return [IndexerTorrent(indexer_account=_account_ref(), torrent_id=TORRENT_ID, download_url="https://ownership.invalid/dl")], []

    async def owner_request():
        try:
            with database.db_session():
                return await getattr(_provider(indexer_method, gated_metadata), provider_method)(key)
        finally:
            owner_closed.set()

    async def joiner_request():
        with database.db_session():
            sources, errors = await getattr(_provider(indexer_method, gated_metadata), provider_method)(key)
            # Response conversion may still run after the owner's response is done.
            await owner_closed.wait()
            source = sources[0]
            assert _orm_instances(source) == []
            return (
                errors,
                source.torrent_file.torrent_id,
                source.torrent_file.info_hash,
                source.indexer_torrent.indexer_account.indexer_definition.name,
            )

    try:
        owner = asyncio.create_task(owner_request())
        await asyncio.wait_for(entered.wait(), 3)
        joiner = asyncio.create_task(joiner_request())
        await asyncio.sleep(0)
        release.set()
        owner_result, joined = await asyncio.wait_for(asyncio.gather(owner, joiner), 5)
    finally:
        await providers._sources_singleflight.cancel_all()

    assert metadata_calls == 1
    assert len(owner_result[0]) == 1
    assert joined == ([], TORRENT_ID, file_db, "Ownership Indexer")


@pytest.mark.anyio
async def test_cancelled_owner_leaves_no_request_session_work_or_checkout(file_db):
    entered, release = asyncio.Event(), asyncio.Event()
    metadata_calls = 0

    async def gated_metadata(_):
        nonlocal metadata_calls
        metadata_calls += 1
        entered.set()
        await release.wait()
        return [IndexerTorrent(indexer_account=_account_ref(), torrent_id=TORRENT_ID, download_url="https://ownership.invalid/dl")], []

    async def request():
        with database.db_session():
            return await _provider("get_torrents_by_imdb_id", gated_metadata).find_by_imdb_id("tt0000022")

    try:
        owner = asyncio.create_task(request())
        await asyncio.wait_for(entered.wait(), 3)
        # The owner's request Session rolls back and closes before the shared read.
        owner.cancel()
        await asyncio.gather(owner, return_exceptions=True)
        joiner = asyncio.create_task(request())
        await asyncio.sleep(0)
        release.set()
        sources, errors = await asyncio.wait_for(joiner, 5)
    finally:
        await providers._sources_singleflight.cancel_all()

    assert metadata_calls == 1
    assert errors == [] and [source.torrent_file.info_hash for source in sources] == [file_db]
    # A shared read on the closed request Session would reopen and keep a connection.
    assert database.SessionLocal.kw["bind"].pool.checkedout() == 0


def test_kodi_indexer_payload_from_ref_matches_orm():
    definition = IndexerDefinitionModel(
        id=INDEXER_ID, name="Ownership Indexer", url="https://ownership.invalid", details_path="/d", supports_totp=True
    )
    account = IndexerAccountModel(indexer_id=INDEXER_ID, username="fixture", password="fixture")
    account.indexer_definition = definition
    ref = IndexerAccountRef.from_model(account)
    stream = TorrentStream(
        indexer_account=ref, torrent_id=TORRENT_ID, info_hash="h", torrent_name="t", file_name="f.mkv",
        file_size=1, file_index=0, play_url="https://ownership.invalid/play", attributes=[ref.indexer_definition],
    )

    payload = KodiImdbStreamsResponse.from_torrent_streams_pair([stream], []).model_dump(by_alias=True)

    assert payload["streams"][0]["indexer"] == IndexerDefinitionResponse.model_validate(definition).model_dump(by_alias=True)
    assert "fixture" not in repr(ref)
