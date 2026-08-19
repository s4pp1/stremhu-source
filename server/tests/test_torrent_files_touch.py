import datetime
import sqlite3
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.common.database import Base, connect_args
from app.modules.torrent_files.repository import TOUCH_THROTTLE, TorrentFilesRepository
from app.modules.torrent_files.schemas import TorrentFileIdentifier

IDENTIFIER = TorrentFileIdentifier(indexer_id="ncore", torrent_id="3374373")


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/app.db", connect_args=connect_args)
    Base.metadata.create_all(engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    engine.dispose()


def _as_sqlite_text(value: datetime.datetime) -> str:
    """A sqlite3 alapértelmezett datetime adaptere 3.12 óta elavult, ezért mi alakítjuk át."""
    return value.isoformat(sep=" ")


def seed(session_factory, last_used_at: datetime.datetime) -> None:
    with session_factory() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        db.execute(
            text(
                "INSERT INTO indexer_accounts (indexer_id, username, password,"
                " hit_and_run, keep_seed_seconds, download_full_torrent, created_at,"
                " updated_at) VALUES ('ncore', 'u', 'p', 0, 0, 0, :now, :now)"
            ),
            {"now": _as_sqlite_text(last_used_at)},
        )
        db.execute(
            text(
                "INSERT INTO torrent_files (indexer_id, torrent_id, info_hash,"
                " torrent_bytes, last_used_at, created_at)"
                " VALUES ('ncore', '3374373', 'hash', X'00', :last_used_at, :now)"
            ),
            {
                "last_used_at": _as_sqlite_text(last_used_at),
                "now": _as_sqlite_text(last_used_at),
            },
        )
        db.commit()


def read_last_used_at(session_factory) -> datetime.datetime:
    with session_factory() as db:
        value = db.execute(text("SELECT last_used_at FROM torrent_files")).scalar_one()
    return datetime.datetime.fromisoformat(value)


def test_touch_updates_a_stale_record(session_factory):
    stale = datetime.datetime.now() - TOUCH_THROTTLE - datetime.timedelta(minutes=1)
    seed(session_factory, stale)

    with session_factory() as db:
        TorrentFilesRepository(db).touch(IDENTIFIER)
        db.commit()

    assert read_last_used_at(session_factory) > stale


def test_touch_skips_a_recently_used_record(session_factory):
    """A lejátszó range kérésenként hív touch-ot: enélkül minden kérés írás lenne."""
    recent = datetime.datetime.now() - TOUCH_THROTTLE / 2
    seed(session_factory, recent)

    with session_factory() as db:
        TorrentFilesRepository(db).touch(IDENTIFIER)
        db.commit()

    assert read_last_used_at(session_factory) == recent


def test_touch_does_not_write_while_another_connection_holds_the_write_lock(
    session_factory, tmp_path
):
    """Throttle esetén a zárolt adatbázis sem okoz hibát."""
    recent = datetime.datetime.now() - TOUCH_THROTTLE / 2
    seed(session_factory, recent)

    holder = sqlite3.connect(f"{tmp_path}/app.db", timeout=10.0, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with session_factory() as db:
            TorrentFilesRepository(db).touch(IDENTIFIER)
            db.commit()
    finally:
        holder.rollback()
        holder.close()

    assert read_last_used_at(session_factory) == recent


def test_touch_is_thread_safe_for_offloaded_calls(session_factory):
    """A stream útvonal külön thread-en hívja: párhuzamosan sem dobhat hibát."""
    stale = datetime.datetime.now() - TOUCH_THROTTLE - datetime.timedelta(minutes=1)
    seed(session_factory, stale)

    errors: list[Exception] = []

    def worker():
        try:
            with session_factory() as db:
                TorrentFilesRepository(db).touch(IDENTIFIER)
                db.commit()
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert read_last_used_at(session_factory) > stale
