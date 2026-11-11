"""SP05/a: one per-tracker search timeout for the IMDb, query and torrent-id searches.

A tracker that does not answer in time becomes a readable error, while the other
trackers' results are kept. Real file SQLite for the account rows; only the
tracker adapters are synthetic doubles.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common import database
from app.common.database import Base
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers import search
from app.modules.indexers.search import IndexerSearchService, invalidate_indexer_cache


class _Torrent(SimpleNamespace):
    pass


def _torrent(torrent_id: str) -> _Torrent:
    return _Torrent(torrent_id=torrent_id, download_url=f"https://fast.invalid/{torrent_id}", imdb_id="tt0000001",
                    seeders=3, attribute_ids=[])


class _Fast:
    async def find_torrents_by_imdb_id(self, imdb_id):
        return [_torrent("fast-imdb")]

    async def find_torrents_by_query(self, query, media_type=None):
        return [_torrent("fast-query")]

    async def find_torrent_by_id(self, torrent_id):
        return _torrent(torrent_id)


class _Slow:
    def __init__(self):
        self.calls = 0

    async def _hang(self, *args, **kwargs):
        self.calls += 1
        await asyncio.sleep(30)

    find_torrents_by_imdb_id = _hang
    find_torrents_by_query = _hang
    find_torrent_by_id = _hang


@pytest.fixture
def two_trackers(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'timeout.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    with session_factory() as db:
        for indexer_id, name in (("fast", "Fast Tracker"), ("slow", "Slow Tracker")):
            definition = IndexerDefinitionModel(id=indexer_id, name=name, url=f"https://{indexer_id}.invalid",
                                                details_path="/")
            account = IndexerAccountModel(indexer_id=indexer_id, username="fixture", password="fixture")
            account.indexer_definition = definition
            db.add_all([definition, account])
        db.commit()
    monkeypatch.setattr(search, "INDEXER_SEARCH_TIMEOUT_SECONDS", 0.05)
    invalidate_indexer_cache()
    adapters = {"fast": _Fast(), "slow": _Slow()}
    service = IndexerSearchService(cast(Any, SimpleNamespace(get_by_id=adapters.__getitem__)))
    try:
        yield service, adapters["slow"]
    finally:
        invalidate_indexer_cache()
        engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "argument", "expected_id"),
    [
        ("get_torrents_by_imdb_id", "tt0000001", "fast-imdb"),
        ("get_torrents_by_query", "fixture title", "fast-query"),
        ("get_torrents_by_torrent_id", "fixture-id", "fixture-id"),
    ],
)
async def test_slow_tracker_times_out_and_fast_results_are_kept(two_trackers, method, argument, expected_id):
    service, _ = two_trackers
    torrents, errors = await asyncio.wait_for(getattr(service, method)(argument), 5)

    assert [t.torrent_id for t in torrents] == [expected_id]
    assert errors == ["A(z) 'Slow Tracker' indexer nem válaszolt időben."]


@pytest.mark.anyio
async def test_timeout_is_not_cached(two_trackers):
    service, slow = two_trackers
    _, first = await service.get_torrents_by_imdb_id("tt0000002")
    _, second = await service.get_torrents_by_imdb_id("tt0000002")

    # A timeout is never cached: the slow tracker is asked again on the next search.
    assert first == second == ["A(z) 'Slow Tracker' indexer nem válaszolt időben."]
    assert slow.calls == 2
