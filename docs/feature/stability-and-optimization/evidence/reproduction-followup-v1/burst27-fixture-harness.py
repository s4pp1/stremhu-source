"""Packet 27 burst input (descriptive): N simultaneous unique-IMDb source searches.

Real path: TorrentSourceProviderService (Singleflight) -> IndexerSearchService (12.5 s
search timeout, tracker cache) -> BaseIndexerDefinition/IndexerClient (shared adapter
semaphore, bounded download) -> _sync_torrent_files (gather) -> IsolatedTorrentFilesService
create_many (native parse, SQLite on tmpfs). Only the adapter's search parser is synthetic:
one JSON search page on the private fixture. Instrumentation wraps, never edits, the source.
"""

import asyncio
import json
import os
import resource
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import httpx

BASE = os.environ["TEST_BASE_URL"]
if httpx.URL(BASE).host != "tracker.fixture.invalid":
    raise RuntimeError("Private fixture required")
N = int(os.environ["BURST_N"])
MIX = os.environ["BURST_MIX"]
RUN = int(os.environ["BURST_RUN"])
K = 40
GUARD_SECONDS = float(os.environ.get("BURST_GUARD_SECONDS", "900"))
SAMPLE_SECONDS = 0.020

from app.common import async_utils, database  # noqa: E402
from app.config import config  # noqa: E402
import app.main  # noqa: E402,F401  (registers every ORM model)
from app.modules.indexer_accounts.models import IndexerAccountModel  # noqa: E402
from app.modules.indexer_definitions.base_indexer_definition import BaseIndexerDefinition  # noqa: E402
from app.modules.indexer_definitions.models import IndexerDefinitionModel  # noqa: E402
from app.modules.indexer_definitions.schemas.internal import (  # noqa: E402
    IndexerDefinitionFindTorrentsResult,
    IndexerDefinitionTorrent,
)
from app.modules.indexers.search import IndexerSearchService  # noqa: E402
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService  # noqa: E402
from app.modules.torrent_source_provider import service as provider_module  # noqa: E402

INDEXER_ID = "burst-fixture"


def cgroup():
    stat = dict(line.split() for line in Path("/sys/fs/cgroup/memory.stat").read_text().splitlines())
    return int(stat["anon"]), int(Path("/sys/fs/cgroup/memory.current").read_text())


def percentile(values, fraction):
    return sorted(values)[int((len(values) - 1) * fraction)] if values else None


class BurstIndexer(BaseIndexerDefinition):
    @property
    def id(self):
        return INDEXER_ID

    @property
    def name(self):
        return "Burst fixture"

    @property
    def url(self):
        return BASE

    @property
    def login_path(self):
        return "/login"

    @property
    def details_path(self):
        return "/details/{torrent_id}"

    @property
    def requires_full_download(self):
        return False

    def _detect_authentication_error(self, response):
        return None

    async def _login(self, payload):
        raise RuntimeError("login is not part of the burst fixture")

    async def _fetch_torrents(self, imdb_id, page=None):
        # Warm-up keys (tt9xxxxxx) always use the typical mix, so the sampled burst starts from the same state.
        mix = "typical" if imdb_id.startswith("tt9") else MIX
        response = await self._client.get("/search", params={"imdb": imdb_id, "mix": mix})
        response.raise_for_status()
        data = response.json()
        return IndexerDefinitionFindTorrentsResult(
            torrents=[IndexerDefinitionTorrent(**item) for item in data["torrents"]], next_page=data["next_page"])

    async def _fetch_torrent(self, torrent_id):
        return None

    async def _fetch_hit_and_run_ids(self):
        return []


class Probe:
    def __init__(self):
        self.inflight = self.inflight_peak = 0
        self.retained = self.retained_peak = 0
        self.downloads = self.download_bytes = 0
        self.store_calls = self.store_items = 0
        self.store_seconds = []
        self.anon_peak = self.current_peak = 0
        self.tasks_peak = 0
        self.lag_max = 0.0

    async def sample(self, stop):
        expected = time.monotonic()
        while not stop.is_set():
            expected += SAMPLE_SECONDS
            await asyncio.sleep(max(0.0, expected - time.monotonic()))
            self.lag_max = max(self.lag_max, time.monotonic() - expected)
            anon, current = cgroup()
            self.anon_peak = max(self.anon_peak, anon)
            self.current_peak = max(self.current_peak, current)
            self.tasks_peak = max(self.tasks_peak, len(asyncio.all_tasks()))


def instrument(probe):
    original_download = IndexerSearchService.download_torrent
    original_store = provider_module._SourceSearch._store_snapshots

    async def download(self, indexer_id, torrent_id, download_url):
        probe.inflight += 1
        probe.inflight_peak = max(probe.inflight_peak, probe.inflight)
        try:
            result = await original_download(self, indexer_id, torrent_id, download_url)
        finally:
            probe.inflight -= 1
        size = len(result.torrent_bytes)
        probe.downloads += 1
        probe.download_bytes += size
        probe.retained += size
        probe.retained_peak = max(probe.retained_peak, probe.retained)
        return result

    def store(self, items):
        began = time.perf_counter()
        try:
            return original_store(self, items)
        finally:
            probe.store_calls += 1
            probe.store_items += len(items)
            probe.store_seconds.append(time.perf_counter() - began)
            probe.retained -= sum(len(item[2]) for item in items)

    IndexerSearchService.download_torrent = download
    provider_module._SourceSearch._store_snapshots = store


def seed():
    Path(config.database_dir).mkdir(parents=True, exist_ok=True)
    database.Base.metadata.create_all(database.engine)
    with database.SessionLocal() as db:
        definition = IndexerDefinitionModel(id=INDEXER_ID, name="Burst fixture", url=BASE, details_path="/details/{torrent_id}")
        account = IndexerAccountModel(indexer_id=INDEXER_ID, username="synthetic", password="synthetic")
        account.indexer_definition = definition
        db.add_all([definition, account])
        db.commit()


async def main():
    original_send = httpx.AsyncClient.send
    outbound = 0

    async def guarded(client, request, *args, **kwargs):
        nonlocal outbound
        if request.url.host != "tracker.fixture.invalid":
            outbound += 1
            raise RuntimeError("External HTTP blocked")
        return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = guarded
    seed()
    probe = Probe()
    instrument(probe)
    adapter = BurstIndexer()
    definitions = SimpleNamespace(get_by_id=lambda indexer_id, include_disabled=False: adapter)
    provider = provider_module.TorrentSourceProviderService(IndexerSearchService(definitions), IsolatedTorrentFilesService())

    # Warm-up (not sampled): imports, native codec, DB, connection pool.
    warm_sources, warm_errors = await provider.find_by_imdb_id(f"tt{9000000 + RUN:07d}")
    await async_utils.drain_background_tasks()
    if len(warm_sources) != K or warm_errors:
        raise RuntimeError("warm-up result mismatch")
    probe.__init__()
    anon_before, current_before = cgroup()
    cpu_before = time.process_time()

    start = asyncio.Event()
    stop = asyncio.Event()
    rows = [None] * N

    async def one(index):
        imdb = f"tt{1000000 + RUN * 1000 + index:07d}"
        await start.wait()
        began = time.perf_counter()
        try:
            sources, errors = await provider.find_by_imdb_id(imdb)
            rows[index] = dict(wall_ms=(time.perf_counter() - began) * 1000, results=len(sources), errors=len(errors),
                               unique_hashes=len({source.torrent_file.info_hash for source in sources}))
        except Exception as error:  # recorded, never fabricated as a result
            rows[index] = dict(wall_ms=(time.perf_counter() - began) * 1000, exception=type(error).__name__)

    sampler = asyncio.create_task(probe.sample(stop))
    workers = [asyncio.create_task(one(index)) for index in range(N)]
    await asyncio.sleep(0.05)
    burst_began = time.perf_counter()
    start.set()
    done, pending = await asyncio.wait(workers, timeout=GUARD_SECONDS)
    burst_seconds = time.perf_counter() - burst_began
    for task in pending:
        task.cancel()
    stop.set()
    await sampler
    await async_utils.drain_background_tasks()
    async with httpx.AsyncClient(base_url=BASE, trust_env=False) as client:
        server = (await client.get("/fixture/stats")).json()
    await adapter.close()
    httpx.AsyncClient.send = original_send
    walls = [row["wall_ms"] for row in rows if row and "results" in row]
    ok = all(row and row.get("results") == K and row.get("errors") == 0 and row.get("unique_hashes") == K for row in rows)
    print(json.dumps(dict(
        fixture="burst27-v1", n=N, mix=MIX, run=RUN, k=K, guard_timeout=bool(pending), ok=ok, rows=rows,
        p50_ms=percentile(walls, 0.5), p95_ms=percentile(walls, 0.95), max_ms=max(walls) if walls else None,
        burst_seconds=burst_seconds, cpu_seconds=time.process_time() - cpu_before,
        anon_before=anon_before, anon_peak_delta=probe.anon_peak - anon_before, current_before=current_before,
        current_peak_delta=probe.current_peak - current_before, tasks_peak=probe.tasks_peak, loop_lag_max_ms=probe.lag_max * 1000,
        downloads=probe.downloads, download_bytes=probe.download_bytes, inflight_peak=probe.inflight_peak,
        retained_downloaded_bytes_peak=probe.retained_peak, store_calls=probe.store_calls, store_items=probe.store_items,
        store_seconds_max=max(probe.store_seconds) if probe.store_seconds else None,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, external_http_attempts=outbound, server=server)))


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
