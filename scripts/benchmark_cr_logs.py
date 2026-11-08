"""Offline logging baseline; never emits the synthetic credential or raw logs."""

import asyncio
import io
import json
import logging
import time

import httpx
from rich.console import Console
from rich.logging import RichHandler

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
    IndexerClient,
)


class FixtureDefinition(BaseIndexerDefinition):
    id = "fixture"
    name = "Fixture"
    url = "https://fixture.invalid"
    login_path = "/login"
    details_path = "/details"
    requires_full_download = False

    def _detect_authentication_error(self, response):
        return None

    async def _login(self, payload):
        raise NotImplementedError

    async def _fetch_torrents(self, imdb_id, page=None):
        raise NotImplementedError

    async def _fetch_torrent(self, torrent_id):
        raise NotImplementedError

    async def _fetch_hit_and_run_ids(self):
        raise NotImplementedError


async def main():
    marker = "synthetic-log-credential-marker"
    output = io.StringIO()
    handler = RichHandler(console=Console(file=output, width=120), rich_tracebacks=True)
    definition = FixtureDefinition()
    await definition._client.aclose()

    def fail(request):
        raise httpx.ReadTimeout(marker, request=request)

    definition._client = IndexerClient(definition, transport=httpx.MockTransport(fail))
    definition.logger.handlers = [handler]
    definition.logger.propagate = False
    definition.logger.setLevel(logging.INFO)
    before = time.process_time()
    for _ in range(1000):
        try:
            await definition.download_torrent(f"https://fixture.invalid/{marker}?key={marker}")
        except Exception:
            pass
    cpu = time.process_time() - before
    await definition.close()
    rendered = output.getvalue()
    print(json.dumps(dict(events=1000, cpu_seconds=cpu, rendered_bytes=len(rendered.encode()), credential_occurrences=rendered.count(marker))))


asyncio.run(main())
