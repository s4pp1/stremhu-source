"""CR15/c (27): the parsed TorrentInfo cache is bounded by file entries, not only by count."""

import pytest

from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.config import config
from app.modules.torrent_files import models


def info(name: str, files: int) -> TorrentInfo:
    return TorrentInfo(info_hash=name, name=name, size=files, piece_size=16384, files=[
        TorrentFileInfo(name=f"{name}-{i}.mkv", path=f"{name}-{i}.mkv", index=i, size=1, offset=i, start_piece_index=0, end_piece_index=0, is_video=True)
        for i in range(files)])


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    monkeypatch.setattr(config, "torrent_info_cache_max_files", 10)
    models._TORRENT_INFO_CACHE.clear()
    yield
    models._TORRENT_INFO_CACHE.clear()


def test_oldest_entries_leave_when_the_file_budget_is_exceeded():
    for name in ("a", "b"):
        models._cache_torrent_info(info(name, 3))  # weight 4 each
    models._cache_torrent_info(info("c", 3))
    assert list(models._TORRENT_INFO_CACHE) == ["b", "c"]


def test_an_entry_larger_than_the_budget_is_not_cached_and_keeps_the_rest():
    models._cache_torrent_info(info("a", 3))
    models._cache_torrent_info(info("huge", 20))
    assert list(models._TORRENT_INFO_CACHE) == ["a"]


def test_reinserting_the_same_hash_does_not_double_count():
    for _ in range(5):
        models._cache_torrent_info(info("a", 3))
    models._cache_torrent_info(info("b", 3))
    assert list(models._TORRENT_INFO_CACHE) == ["a", "b"]


def test_external_clear_resets_the_accounting():
    models._cache_torrent_info(info("a", 8))
    models._TORRENT_INFO_CACHE.clear()
    models._cache_torrent_info(info("b", 8))
    assert list(models._TORRENT_INFO_CACHE) == ["b"]
