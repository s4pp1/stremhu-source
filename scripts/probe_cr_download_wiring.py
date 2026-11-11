"""Actual IndexerClient HTTP/auth/redirect/decoding fixture, not a G15 gate."""

import asyncio
import gc
import hashlib
import json
import os
import time

import httpx
import libtorrent

from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.indexer_definitions.schemas.internal import AuthSessionError


BASE_URL = os.environ["TEST_BASE_URL"]
ALLOWED_HOSTS = {"tracker.fixture.invalid", "cdn.other.invalid"}


async def main():
    original_send = httpx.AsyncClient.send
    blocked = 0

    async def offline_send(client, request, *args, **kwargs):
        nonlocal blocked
        if request.url.host not in ALLOWED_HOSTS:
            blocked += 1
            raise RuntimeError("Synthetic tracker fixture blocked external HTTP")
        return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = offline_send
    adapter = NcoreIndexerDefinition()
    rows = []
    logins = 0
    try:
        await adapter._client.aclose()
        adapter._client = IndexerClient(adapter, base_url=BASE_URL, follow_redirects=True,
                                        timeout=20, trust_env=False)
        adapter._semaphore = asyncio.Semaphore(1)

        def auth_error(response):
            return AuthSessionError() if response.headers.get("X-Fixture-Auth-Required") == "1" else None

        async def login(credential=None):
            nonlocal logins
            logins += 1
            response = await adapter._client.post("/fixture/login", content=b"synthetic")
            response.raise_for_status()

        adapter._detect_authentication_error = auth_error
        adapter.login = login
        expected = {"small": 82073, "many-files": 1362823, "large-valid": 21491624,
                    "login-redirect": 82073, "cdn-redirect": 82073,
                    "chunked-large": 64 << 20, "gzip-large": 128 << 20, "drip": 40960}
        for kind, size in expected.items():
            started = time.perf_counter()
            async with asyncio.timeout(30):
                body = await adapter.download_torrent(BASE_URL + "/payload/" + kind)
            if len(body) != size:
                raise RuntimeError("Synthetic download body size differs")
            state = "accepted"
            try:
                native = libtorrent.torrent_info(body)
                del native
            except RuntimeError:
                state = "rejected"
            if (state == "accepted") != (kind in {"small", "many-files", "large-valid", "login-redirect", "cdn-redirect"}):
                raise RuntimeError("Synthetic native content validation differs")
            rows.append(dict(kind=kind, decoded_bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                             native_state=state, wall_seconds=time.perf_counter()-started))
            del body
            gc.collect()
        async with httpx.AsyncClient(base_url=BASE_URL, trust_env=False) as client:
            stats = (await client.get("/fixture/stats")).json()
        if logins != 1 or stats.get("foreign-cookie-present", 0) or blocked:
            raise RuntimeError("Synthetic auth/foreign-cookie boundary differs")
    finally:
        await adapter.close()
        httpx.AsyncClient.send = original_send
    print(json.dumps(dict(fixture="g15-real-http-auth-decoding-wiring-v1", is_measurement=False,
                          rows=rows, login_calls=logins, max_concurrent=1, server_counts=stats,
                          external_http_blocked=blocked,
                          scope="Private local HTTP tracker/CDN, actual IndexerClient and relogin, native parsing. Single wiring pass;4s drip is not an overall-deadline gate. No size/origin/admission policy selected.")))


asyncio.run(main())
