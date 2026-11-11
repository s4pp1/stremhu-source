from unittest.mock import AsyncMock, MagicMock

import libtorrent
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common.database import Base, connect_args
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.stremio.schemas import ImdbStreamId, StremioStream
from app.modules.stremio.service import (
    StremioService,
    get_user_cache_generation,
    invalidate_stream_cache,
)
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.users.models import UserModel


def test_user_stream_cache_invalidation_and_generations():
    """M05: User generáció növelése és cache ürítése explicit invalidáláskor."""
    user = UserModel(
        id="user_test_123",
        username="testuser",
        api_key="api_key_v1",
        enable_stream_deduplication=True,
        enable_fallback_subtitles=False,
        enable_smart_filter=True,
        smart_filter_limit=10,
    )

    initial_gen = get_user_cache_generation(user.id)
    assert initial_gen >= 0

    # Invalidálás az adott userre
    invalidate_stream_cache(user.id)
    new_gen = get_user_cache_generation(user.id)
    assert new_gen == initial_gen + 1

    # Globális invalidálás
    invalidate_stream_cache(None)
    assert get_user_cache_generation(user.id) == 0


@pytest.mark.anyio
async def test_stream_service_respects_cache_invalidation():
    """M05: Invalidálás után az új lekérés nem a cache-ből tér vissza."""
    user = UserModel(
        id="user_cache_test",
        username="testuser",
        api_key="api_key_v1",
        enable_stream_deduplication=True,
        enable_fallback_subtitles=False,
        enable_smart_filter=True,
        smart_filter_limit=10,
    )
    parsed_id = ImdbStreamId(imdb_id="tt1375666")

    mock_torrent_streams_service = MagicMock()
    mock_settings_service = MagicMock()
    mock_settings_service.get_app_url.return_value = "http://localhost:7070"

    stream_mock = StremioStream(
        name="Stream 1",
        description="Test description",
        url="http://localhost:7070/play/1",
    )
    mock_torrent_streams_service.find_by_imdb.return_value = ([], [])

    service = StremioService(
        torrent_streams_service=mock_torrent_streams_service,
        settings_service=mock_settings_service,
    )
    service._get_streams_uncached = AsyncMock(return_value=[stream_mock])  # type: ignore

    # Első hívás: cache-eli
    res1 = await service.get_streams(user, parsed_id)
    assert len(res1) == 1
    assert service._get_streams_uncached.call_count == 1

    # Második hívás azonos generációval: cache hit
    res2 = await service.get_streams(user, parsed_id)
    assert len(res2) == 1
    assert service._get_streams_uncached.call_count == 1

    # Invalidálás userre
    invalidate_stream_cache(user.id)

    # Harmadik hívás: új uncached hívás indul
    res3 = await service.get_streams(user, parsed_id)
    assert len(res3) == 1
    assert service._get_streams_uncached.call_count == 2


def test_torrent_files_repository_create_many_ignore_duplicates(tmp_path):
    """M10: Duplicate indexer_id + torrent_id beszúrás nem dob IntegrityError-t."""
    engine = create_engine(f"sqlite:///{tmp_path}/test_app.db", connect_args=connect_args)
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_cls() as db:
        definition = IndexerDefinitionModel(
            id="test_indexer_m10",
            name="Test Indexer M10",
            url="https://test.invalid",
            details_path="/",
        )
        account = IndexerAccountModel(
            indexer_id="test_indexer_m10",
            username="user",
            password="pwd",
        )
        account.indexer_definition = definition
        db.add(definition)
        db.add(account)
        db.commit()

        dummy_torrent_bytes = libtorrent.bencode(
            {
                b"info": {
                    b"name": b"test_torrent",
                    b"piece length": 16384,
                    b"pieces": b"\0" * 20,
                    b"length": 1024,
                }
            }
        )
        model1 = TorrentFileModel(
            indexer_id="test_indexer_m10",
            torrent_id="tid_1",
            torrent_bytes=dummy_torrent_bytes,
        )
        repo = TorrentFilesRepository(db)
        repo.create(model1)
        db.commit()

        model1_dup = TorrentFileModel(
            indexer_id="test_indexer_m10",
            torrent_id="tid_1",
            torrent_bytes=dummy_torrent_bytes,
        )
        model2 = TorrentFileModel(
            indexer_id="test_indexer_m10",
            torrent_id="tid_2",
            torrent_bytes=dummy_torrent_bytes,
        )

        # Nem dob IntegrityError-t az ON CONFLICT DO NOTHING miatt
        repo.create_many_ignore_duplicates([model1_dup, model2])
        db.commit()

        saved1 = repo.find_by_id("test_indexer_m10", "tid_1")
        saved2 = repo.find_by_id("test_indexer_m10", "tid_2")
        assert saved1 is not None
        assert saved2 is not None

    engine.dispose()
