"""SP06/a: a failed Tech Info lookup is not cached as an empty result for an hour.

The nCore adapter reports transport errors, 5xx and 429 as TechInfoUnavailableException,
while "no NFO / empty description" stays a normal (None, None)-style result. The
enrichment caches only real results.
"""

import logging
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest

from app.modules.indexer_definitions.exceptions import TechInfoUnavailableException
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.media_attributes import tech_info_cache
from app.modules.torrent_streams.service import TorrentStreamsService

MEDIAINFO_NFO = "General\nAudio #1\nLanguage : Hungarian\n"


def _response(status: int, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(status_code=status, text=text)


def _adapter(*responses) -> tuple[NcoreIndexerDefinition, AsyncMock]:
    adapter = object.__new__(NcoreIndexerDefinition)
    adapter.logger = logging.getLogger("sp06a-test")
    client = AsyncMock()
    client.get.side_effect = list(responses)
    adapter._client = client
    return adapter, client


@pytest.mark.anyio
@pytest.mark.parametrize(
    "responses",
    [
        [httpx.ReadTimeout("synthetic")],
        [_response(503)],
        [_response(404), _response(429)],
        [_response(200, ""), httpx.ConnectError("synthetic")],
    ],
    ids=["nfo-timeout", "nfo-5xx", "drop-429", "drop-connect-error"],
)
async def test_failed_lookup_raises_unavailable(responses):
    adapter, _ = _adapter(*responses)
    with pytest.raises(TechInfoUnavailableException):
        await adapter.fetch_tech_info("1")


@pytest.mark.anyio
async def test_no_data_is_a_normal_result():
    adapter, client = _adapter(_response(404), _response(200, "  "))
    assert await adapter.fetch_tech_info("1") == (None, None)
    assert client.get.await_count == 2


@pytest.mark.anyio
async def test_complete_nfo_skips_the_second_request():
    adapter, client = _adapter(_response(200, MEDIAINFO_NFO))
    assert await adapter.fetch_tech_info("1") == (MEDIAINFO_NFO, None)
    assert client.get.await_count == 1


@pytest.mark.anyio
async def test_enrichment_caches_results_but_not_failures(monkeypatch):
    monkeypatch.setattr(tech_info_cache, "_TECH_INFO_CACHE", {})
    service = object.__new__(TorrentStreamsService)
    failing = SimpleNamespace(fetch_tech_info=AsyncMock(side_effect=TechInfoUnavailableException("x")))
    empty = SimpleNamespace(fetch_tech_info=AsyncMock(return_value=(None, None)))
    adapters = {"failing": failing, "empty": empty}
    service._indexer_definitions_service = cast(Any, SimpleNamespace(get_by_id=adapters.__getitem__))

    await service._enrich_torrent_group(("failing", "1"), [])
    await service._enrich_torrent_group(("failing", "1"), [])
    await service._enrich_torrent_group(("empty", "1"), [])
    await service._enrich_torrent_group(("empty", "1"), [])

    assert ("failing", "1") not in tech_info_cache._TECH_INFO_CACHE
    assert failing.fetch_tech_info.await_count == 2  # retried, not poisoned for an hour
    assert ("empty", "1") in tech_info_cache._TECH_INFO_CACHE
    assert empty.fetch_tech_info.await_count == 1  # a real (empty) result is cached
