import datetime

import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.modules.playback_histories.models import PlaybackHistoryModel
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentKey

NOW = datetime.datetime(2026, 8, 11, 12, 0, 0)
LONG_AGO = NOW - datetime.timedelta(days=30)


def add_torrent(
    db: Session,
    info_hash: str,
    torrent_id: str,
    created_at: datetime.datetime,
    is_persisted: bool = False,
):
    db.execute(
        insert(TorrentModel).values(
            info_hash=info_hash,
            indexer_id="ncore",
            torrent_id=torrent_id,
            is_persisted=is_persisted,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def add_playback(db: Session, torrent_id: str, created_at: datetime.datetime):
    db.execute(
        insert(PlaybackHistoryModel).values(
            playback_id=f"pb-{torrent_id}-{created_at.timestamp()}",
            user_id="user-1",
            indexer_id="ncore",
            torrent_id=torrent_id,
            file_index=0,
            torrent_name="torrent",
            file_name="file.mkv",
            created_at=created_at,
        )
    )


@pytest.fixture
def repository(db: Session):
    # regen hozzáadva, de tegnap nézve -> utoljára törlendő
    add_torrent(db, "tegnap_nezett", "1", LONG_AGO)
    add_playback(db, "1", NOW - datetime.timedelta(days=1))

    # 2 napja hozzáadva, sosem nézve -> a created_at számít
    add_torrent(db, "sosem_nezett", "2", NOW - datetime.timedelta(days=2))

    # regen hozzáadva és regen nézve -> elsőként törlendő
    add_torrent(db, "regen_nezett", "3", LONG_AGO)
    add_playback(db, "3", LONG_AGO + datetime.timedelta(days=1))

    # seedben tartás bekapcsolva -> sosem törölhető
    add_torrent(db, "seedben_tartott", "4", LONG_AGO, is_persisted=True)

    # épp most hozzáadva -> az LRU sorrend miatt magától a lista végére kerül
    add_torrent(db, "frissen_hozzaadott", "5", NOW - datetime.timedelta(minutes=5))

    db.flush()

    return TorrentRepository(db)


def test_orders_by_least_recently_watched_and_skips_seeded(
    repository: TorrentRepository,
):
    torrents = repository.find_for_storage_cleanup()

    # A "seedben_tartott" hiánya szándékos: azt sosem adjuk vissza törlésre.
    assert [t.info_hash for t in torrents] == [
        "regen_nezett",
        "sosem_nezett",
        "tegnap_nezett",
        "frissen_hozzaadott",
    ]


def test_excludes_info_hashes(repository: TorrentRepository):
    torrents = repository.find_for_storage_cleanup(
        excluded_info_hashes=["regen_nezett", "sosem_nezett"]
    )

    assert [t.info_hash for t in torrents] == [
        "tegnap_nezett",
        "frissen_hozzaadott",
    ]


def test_excludes_torrent_keys_only_for_the_matching_indexer(
    repository: TorrentRepository,
):
    torrents = repository.find_for_storage_cleanup(
        excluded_torrent_keys=[
            TorrentKey(indexer_id="ncore", torrent_id="3"),
            TorrentKey(indexer_id="ncore", torrent_id="1"),
            # Ugyanaz a torrent_id, de másik indexer -> nem szabad kizárnia a "2"-t.
            TorrentKey(indexer_id="masik", torrent_id="2"),
        ]
    )

    assert [t.info_hash for t in torrents] == [
        "sosem_nezett",
        "frissen_hozzaadott",
    ]
