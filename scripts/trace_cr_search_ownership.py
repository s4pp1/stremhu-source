"""G17 baseline: real provider/repository/SQLite, synthetic gated metadata.

No network or dotenv. Events contain opaque session/thread IDs, never SQL values.
Alias instrumentation serializes DBAPI execution after detecting overlapping
Session calls, so the fixture observes the existing ownership violation without
deliberately executing a shared mutable Session concurrently in SQLite.
This trace is not a heap-growth or memory-leak experiment.
"""

import asyncio
import json
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_source_provider import service as providers


async def main():
    traces = []
    with tempfile.TemporaryDirectory() as directory:
        engine = create_engine(
            f"sqlite:///{Path(directory) / 'ownership.db'}",
            connect_args={"check_same_thread": False},
            hide_parameters=True,
        )
        database.Base.metadata.create_all(engine)
        events = []
        session_counter = 0
        marker_lock = threading.Lock()
        dbapi_lock = threading.Lock()
        alias_barrier = None
        alias_reads_met: list[bool] = []

        class TrackedSession(Session):
            def __init__(self, *args, **kwargs):
                nonlocal session_counter
                super().__init__(*args, **kwargs)
                with marker_lock:
                    session_counter += 1
                    self.trace_id = session_counter
                self.owner_closed = False
                self.active_calls = 0
                self.mark("create")

            def mark(self, kind, **fields):
                with marker_lock:
                    events.append(dict(
                        time_ns=time.monotonic_ns(), session=self.trace_id,
                        thread=threading.get_ident(), kind=kind,
                        owner_closed=self.owner_closed,
                        active_calls=self.active_calls, **fields,
                    ))

            def execute(self, *args, **kwargs):
                with marker_lock:
                    self.active_calls += 1
                self.mark("use-begin")
                try:
                    if alias_barrier is not None:
                        try:
                            alias_barrier.wait(timeout=3)
                        except threading.BrokenBarrierError:
                            # Packet22b: the shared-read gate serializes the two reads,
                            # so they never meet; overlap detection below is unchanged.
                            alias_reads_met.append(False)
                    with dbapi_lock:
                        return super().execute(*args, **kwargs)
                finally:
                    self.mark("use-end")
                    with marker_lock:
                        self.active_calls -= 1

            def commit(self):
                self.mark("commit")
                return super().commit()

            def rollback(self):
                self.mark("rollback")
                return super().rollback()

            def close(self):
                self.mark("close")
                self.owner_closed = True
                return super().close()

        database.SessionLocal = sessionmaker(
            bind=engine, class_=TrackedSession, autoflush=False,
        )

        class NoTouchFiles(IsolatedTorrentFilesService):
            # Touch ownership is inventoried separately. No background writes
            # are needed to trace the shared read in this fixture.
            def touch(self, identifiers):
                return None

        def new_provider(db, indexers):
            # Since CR17/d the provider takes no request Session; db stays the
            # request's own Session so the trace still sees its lifecycle.
            return providers.TorrentSourceProviderService(
                indexers_service=indexers,
                isolated_torrent_files_service=NoTouchFiles(),
            )

        async def drain_registry():
            await providers._sources_singleflight.cancel_all()
            await providers._single_source_singleflight.cancel_all()
            await providers._torrent_download_singleflight.cancel_all()

        def capture(name, start, **extra):
            recorded = list(events[start:])
            traces.append(dict(
                case=name, events=recorded,
                owner_close_before_use=any(e["kind"] == "use-begin" and e["owner_closed"] for e in recorded),
                overlapping_session_calls=any(e["active_calls"] > 1 for e in recorded),
                pool_checked_out=engine.pool.checkedout(), **extra,
            ))

        # (a) A cancelled waiter exits its real db_session. A second request
        # rejoins the shielded provider task before its delayed DB read.
        start = len(events)
        entered, release = asyncio.Event(), asyncio.Event()
        owned = []
        calls = 0

        async def gated_indexer(_):
            nonlocal calls
            calls += 1
            entered.set()
            await release.wait()
            return [], []

        indexers = SimpleNamespace(get_torrents_by_imdb_id=gated_indexer)

        async def request_owner():
            with database.db_session() as db:
                owned.append(db)
                return await new_provider(db, indexers).find_by_imdb_id("tt0000001")

        owner = asyncio.create_task(request_owner())
        await asyncio.wait_for(entered.wait(), 3)
        owner.cancel()
        await asyncio.gather(owner, return_exceptions=True)
        joiner = asyncio.create_task(request_owner())
        await asyncio.sleep(0)
        release.set()
        joined = await asyncio.wait_for(joiner, 3)
        capture("owner-cancel-then-rejoin", start, metadata_calls=calls,
                joined_result_correct=joined == ([], []))
        # Any checkout reopened after the original owner's close is explicitly
        # released by the fixture after the evidence has been captured.
        for db in owned:
            db.close()
        await drain_registry()

        # (b) Ordinary two-request same-key sharing preserves deduplication.
        start = len(events)
        entered, release = asyncio.Event(), asyncio.Event()
        owned, calls = [], 0
        first = asyncio.create_task(request_owner())
        await asyncio.wait_for(entered.wait(), 3)
        second = asyncio.create_task(request_owner())
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.wait_for(asyncio.gather(first, second), 3)
        capture("two-request-same-key", start, metadata_calls=calls,
                results_correct=results == [([], []), ([], [])])
        await drain_registry()

        # (c) The actual public provider API starts the same read from two
        # alias keys against the request's one Session in two to_thread calls.
        start = len(events)
        alias_barrier = threading.Barrier(2)

        async def immediate_indexer(_):
            return [], []

        with database.db_session() as db:
            provider = new_provider(db, SimpleNamespace(get_torrents_by_imdb_id=immediate_indexer))
            results = await asyncio.wait_for(asyncio.gather(
                provider.find_by_imdb_id("tt0000002"),
                provider.find_by_imdb_id("tt0000003"),
            ), 5)
        alias_barrier = None
        capture("two-alias-reads", start, results_correct=results == [([], []), ([], [])],
                dbapi_serialized_by_fixture=True, alias_reads_met=not alias_reads_met)
        await drain_registry()

        # (d) Cancelling a singleflight during a blocked worker does not finish
        # that worker. Record the owner close while its real read is still live.
        start = len(events)
        thread_entered, thread_release = threading.Event(), threading.Event()
        finished = threading.Event()

        class BlockingFiles(NoTouchFiles):
            def find_snapshots(self, identifiers):
                thread_entered.set()
                if not thread_release.wait(3):
                    raise TimeoutError("Synthetic worker gate timed out")
                try:
                    return super().find_snapshots(identifiers)
                finally:
                    finished.set()

        db = database.SessionLocal()
        provider = providers.TorrentSourceProviderService(
            indexers_service=SimpleNamespace(get_torrents_by_imdb_id=immediate_indexer),
            isolated_torrent_files_service=BlockingFiles(),
        )
        waiting = asyncio.create_task(provider.find_by_imdb_id("tt0000004"))
        assert await asyncio.to_thread(thread_entered.wait, 3)
        closing = asyncio.create_task(providers._sources_singleflight.cancel_all())
        # Observe admission/closure before releasing from an independent
        # controller. A correct owned-thread close must not deadlock a fixture
        # that releases its worker only after close has returned.
        for _ in range(3):
            await asyncio.sleep(0)
        close_returned_before_release = closing.done()
        if close_returned_before_release:
            await closing
            worker_finished_at_cancel_return = finished.is_set()
            db.close()
            thread_release.set()
        else:
            thread_release.set()
            await closing
            worker_finished_at_cancel_return = finished.is_set()
            db.close()
        await asyncio.gather(waiting, return_exceptions=True)
        assert await asyncio.to_thread(finished.wait, 3)
        capture("shutdown-during-worker", start,
                worker_finished_at_cancel_return=worker_finished_at_cancel_return,
                close_returned_before_worker_release=close_returned_before_release)
        db.close()
        await drain_registry()
        final_checkout = engine.pool.checkedout()
        engine.dispose()
    print(json.dumps(dict(
        fixture="g17-real-provider-file-db-ownership-v3", traces=traces,
        fixture_cleanup_final_checkouts=final_checkout,
        scope="Production provider, Singleflight, repository and db_session; gated synthetic indexer. Alias DBAPI calls serialized after detecting overlap. No heap or leak claim.",
    )))


asyncio.run(main())
