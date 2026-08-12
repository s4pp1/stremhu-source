from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.torrents.schemas.internal import TorrentKey
from app.modules.torrents.service import TorrentsService

GB = 1024 * 1024 * 1024


def create_relay_torrent(info_hash: str, downloaded: int):
    return SimpleNamespace(info_hash=info_hash, downloaded=downloaded, name=info_hash)


class FakeRelayService:
    def __init__(self, relay_torrents):
        self._relay_torrents = {t.info_hash: t for t in relay_torrents}
        self.deleted: list[str] = []

    def get_torrents(self):
        return list(self._relay_torrents.values())

    def delete_torrent(self, info_hash: str) -> bool:
        if info_hash not in self._relay_torrents:
            return False

        self.deleted.append(info_hash)
        del self._relay_torrents[info_hash]
        return True


class FakeTorrentRepository:
    """A jelölteket a repository által garantált LRU sorrendben adja vissza."""

    def __init__(self, candidate_info_hashes):
        self._candidates = [
            SimpleNamespace(
                info_hash=info_hash, indexer_id="ncore", torrent_id=info_hash
            )
            for info_hash in candidate_info_hashes
        ]
        self.deleted: list[str] = []
        self.last_kwargs: dict = {}

    def find_for_storage_cleanup(self, **kwargs):
        self.last_kwargs = kwargs
        return [c for c in self._candidates if c.info_hash not in self.deleted]

    def delete(self, info_hash: str):
        self.deleted.append(info_hash)


def create_service(relay_torrents, candidate_info_hashes):
    relay_service = FakeRelayService(relay_torrents)
    torrent_repository = FakeTorrentRepository(candidate_info_hashes)

    service = TorrentsService(
        torrent_repository=torrent_repository,
        torrent_files_service=Mock(),
        indexer_accounts_service=Mock(),
        indexer_definitions_service=Mock(),
        relay_service=relay_service,
    )

    return service, relay_service, torrent_repository


@pytest.mark.parametrize(
    "max_storage_bytes",
    [
        pytest.param(100 * GB, id="kvota_alatt"),
        pytest.param(0, id="kvota_kikapcsolva"),
    ],
)
def test_does_nothing_when_there_is_no_work(max_storage_bytes: int):
    service, relay_service, _ = create_service(
        [create_relay_torrent("a", 10 * GB), create_relay_torrent("b", 10 * GB)],
        ["a", "b"],
    )

    assert service.cleanup_storage_quota(max_storage_bytes) == 0
    assert relay_service.deleted == []


def test_deletes_only_as_much_as_the_quota_requires():
    # 10 x 10GB használat, 50GB kvóta -> pontosan 5 torrentet kell törölni,
    # a repository által adott sorrendben.
    service, relay_service, _ = create_service(
        [create_relay_torrent(info_hash, 10 * GB) for info_hash in "abcdefghij"],
        list("abcdefghij"),
    )

    freed_bytes = service.cleanup_storage_quota(50 * GB)

    assert freed_bytes == 50 * GB
    assert relay_service.deleted == list("abcde")
    assert service.get_used_storage_bytes() == 50 * GB


def test_deletes_the_orphan_row_without_counting_bytes():
    # Az 'arva' rekordot a relay már nem ismeri, így nem szabadít fel helyet.
    service, relay_service, torrent_repository = create_service(
        [create_relay_torrent("b", 60 * GB), create_relay_torrent("c", 40 * GB)],
        ["arva", "b", "c"],
    )

    freed_bytes = service.cleanup_storage_quota(50 * GB)

    assert freed_bytes == 60 * GB
    assert "arva" in torrent_repository.deleted
    assert "arva" not in relay_service.deleted
    assert relay_service.deleted == ["b"]


def test_survives_when_every_torrent_is_protected():
    service, relay_service, _ = create_service(
        [create_relay_torrent("a", 100 * GB)],
        [],  # a repository semmit nem ad vissza, mert minden védett
    )

    assert service.cleanup_storage_quota(10 * GB) == 0
    assert relay_service.deleted == []


def test_forwards_the_exclusions_to_the_repository():
    service, _, torrent_repository = create_service(
        [create_relay_torrent("a", 100 * GB)], ["a"]
    )

    service.cleanup_storage_quota(
        10 * GB,
        excluded_info_hashes=["streamelt"],
        excluded_torrent_keys=[TorrentKey(indexer_id="ncore", torrent_id="42")],
    )

    assert torrent_repository.last_kwargs == {
        "excluded_info_hashes": ["streamelt"],
        "excluded_torrent_keys": [TorrentKey(indexer_id="ncore", torrent_id="42")],
    }
