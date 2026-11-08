import asyncio
import builtins
import io
import logging
import traceback
from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from hypercorn.config import Config as HypercornConfig
from hypercorn.logging import Logger as HypercornLogger
from hypercorn.typing import WWWScope
from rich.console import Console
from rich.logging import RichHandler

from app.common.log_safety import (
    SAFE_ACCESS_LOG_FORMAT,
    SensitiveNetworkLogFilter,
    network_error_fields,
)
from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.exceptions import IndexerDefinitionException
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
from app.modules.network.ddns.providers.duckdns import DuckDnsProvider
from app.modules.network.ddns.providers.myaddr import MyAddrProvider
from app.modules.network.ddns.schemas.internal import DDNSIpUpdate

MARKER = "synthetic-sensitive-log-marker"


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["timeout", "status"])
async def test_download_error_and_wrapped_traceback_are_safe(caplog, failure):
    adapter = NcoreIndexerDefinition()
    await adapter._client.aclose()

    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout(f"cookie={MARKER}", request=request)
        return httpx.Response(403, request=request, text=MARKER)

    adapter._client = IndexerClient(adapter, transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(IndexerDefinitionException) as error:
            # The tracker's own domain (26b host policy); the transport is mocked.
            await adapter.download_torrent(f"https://ncore.pro/{MARKER}?key={MARKER}")
        rendered = "".join(traceback.format_exception(error.value))
        assert MARKER not in rendered
        assert MARKER not in caplog.text
        assert "download" in caplog.text
        assert "ncore" in caplog.text
        if failure == "status":
            assert "403" in caplog.text
        summary = network_error_fields(error.value)
        assert MARKER not in repr(summary)
    finally:
        await adapter.close()


@pytest.mark.anyio
@pytest.mark.parametrize("provider_type", [DuckDnsProvider, MyAddrProvider])
@pytest.mark.parametrize("failure", ["timeout", "status", "body"])
async def test_ddns_error_chain_does_not_reemit_token(monkeypatch, caplog, provider_type, failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout(MARKER, request=request)
        return httpx.Response(403 if failure == "status" else 200, request=request, text=MARKER)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    with pytest.raises(RuntimeError) as error:
        await provider_type().update(DDNSIpUpdate(provider_token=MARKER, host="fixture.invalid", ip="192.0.2.1"))
    assert MARKER not in "".join(traceback.format_exception(error.value))
    assert MARKER not in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [200, 302, 403, 500])
async def test_real_hypercorn_access_formatter_has_no_request_target(status_code):
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    access = logging.Logger("fixture-access", level=logging.INFO)
    access.addHandler(handler)
    configuration = HypercornConfig()
    configuration.accesslog = access
    configuration.access_log_format = SAFE_ACCESS_LOG_FORMAT
    log = HypercornLogger(configuration)
    scope = dict(type="http", method="GET", path=f"/api/{MARKER}/stream/{MARKER}", raw_path=b"/", query_string=f"key={MARKER}".encode(), headers=[(b"cookie", MARKER.encode())], http_version="1.1", scheme="https", server=("fixture.invalid", 443), client=("192.0.2.1", 1234))
    await log.access(cast(WWWScope, scope), {"status": status_code, "headers": []}, 0.1)
    assert MARKER not in output.getvalue()
    assert f"GET {status_code}" in output.getvalue()


def test_actual_rich_handler_drops_library_url_and_exception_records():
    output = io.StringIO()
    handler = RichHandler(console=Console(file=output, width=160), rich_tracebacks=True, show_path=False)
    handler.addFilter(SensitiveNetworkLogFilter())
    logger = logging.Logger("fixture", level=logging.DEBUG)
    logger.addHandler(handler)
    for name in ["httpx", "httpcore", "httpcore.connection"]:
        record = logging.LogRecord(name, logging.INFO, __file__, 1, MARKER, (), None)
        handler.handle(record)
        assert output.getvalue() == ""
    logger.error("operation=download status=403 kind=HTTPStatusError")
    assert MARKER not in output.getvalue()
    assert "403" in output.getvalue()


@pytest.mark.parametrize("mode", ["trace", "wrapped-trace", "argument"])
def test_real_rich_handler_sanitizes_unhandled_network_error_chain(mode):
    output = io.StringIO()
    handler = RichHandler(console=Console(file=output, width=160), rich_tracebacks=True, show_path=False)
    handler.addFilter(SensitiveNetworkLogFilter())
    log = logging.Logger("fixture-application", level=logging.DEBUG)
    log.addHandler(handler)
    request = httpx.Request("GET", f"https://fixture.invalid/{MARKER}?key={MARKER}")
    response = httpx.Response(403, request=request, text=MARKER)
    error = httpx.HTTPStatusError(MARKER, request=request, response=response)
    if mode == "argument":
        log.error("operation failed: %s", error)
    else:
        try:
            try:
                raise error
            except httpx.HTTPStatusError as cause:
                if mode == "wrapped-trace":
                    raise RuntimeError(MARKER) from cause
                raise
        except Exception:
            log.exception(f"operation failed: {MARKER}")
    rendered = output.getvalue()
    assert MARKER not in rendered
    assert "HTTPStatusError" in rendered
    assert "403" in rendered


@pytest.mark.parametrize("shape", ["deep-chain", "large-group", "large-args"])
def test_network_handler_chain_budget_does_not_expose_uninspected_tail(shape):
    output = io.StringIO()
    handler = RichHandler(console=Console(file=output, width=160), rich_tracebacks=True, show_path=False)
    handler.addFilter(SensitiveNetworkLogFilter())
    log = logging.Logger("fixture-application", level=logging.DEBUG)
    log.addHandler(handler)
    error: BaseException = sensitive_network_failure()
    if shape == "deep-chain":
        for _ in range(70):
            outer = RuntimeError(MARKER)
            outer.__cause__ = error
            error = outer
    elif shape == "large-group":
        repeated = ValueError("ordinary synthetic error")
        error = builtins.ExceptionGroup(MARKER, [repeated]*64 + [cast(Exception, error)])
    if shape == "large-args":
        log.error("%s "*65, *(["ordinary"]*64 + [error]))
    else:
        log.error("operation failed", exc_info=(type(error), error, None))
    assert MARKER not in output.getvalue()
    assert "ExceptionChainLimit" in output.getvalue()


@pytest.mark.anyio
@pytest.mark.parametrize("stage", ["directory", "account", "order", "poll-cleanup", "deadline"])
async def test_acme_public_error_and_cleanup_chain_does_not_reemit_network_data(monkeypatch, caplog, stage):
    from app.modules.network.ssl import service as ssl_module
    from app.modules.network.ssl.schemas import AcmeCertificateGenerate

    def failure():
        return httpx.ReadTimeout(MARKER, request=httpx.Request("GET", f"https://fixture.invalid/{MARKER}"))

    challenge = SimpleNamespace(typ="dns-01", validation=lambda key:MARKER, response=lambda key:None)
    order = SimpleNamespace(authorizations=[SimpleNamespace(body=SimpleNamespace(challenges=[SimpleNamespace(chall=challenge)]))])
    acme = Mock()
    acme.net = SimpleNamespace(account=None)
    acme.new_order.return_value = order
    if stage == "account":
        acme.new_account.side_effect = failure()
    elif stage == "order":
        acme.new_order.side_effect = failure()
    elif stage == "deadline":
        acme.new_order.side_effect = TimeoutError(MARKER)
    acme.poll_and_finalize.side_effect = failure()

    class Client:
        @staticmethod
        def get_directory(url, network):
            if stage == "directory":
                raise failure()
            return Mock()

        def __new__(cls, *args, **kwargs):
            return acme

    monkeypatch.setattr(ssl_module.client, "ClientV2", Client)
    monkeypatch.setattr(ssl_module.client, "ClientNetwork", lambda key:Mock())
    monkeypatch.setattr(ssl_module, "wait_for_dns_propagation", AsyncMock(return_value=True))
    ddns = Mock()
    ddns.update = AsyncMock(side_effect=[None, RuntimeError(MARKER)])
    service = ssl_module.SslService(ddns)
    payload = AcmeCertificateGenerate(ddns_provider_id="fixture", ddns_provider_token=MARKER, host="fixture.invalid", email="operator@fixture.invalid")
    with pytest.raises(TimeoutError if stage == "deadline" else ValueError) as error:
        await service.generate_acme_certificate(payload)
    assert MARKER not in "".join(traceback.format_exception(error.value))
    assert MARKER not in caplog.text
    if stage != "directory":
        acme.new_account.assert_called_once()
    if stage not in {"directory", "account"}:
        acme.new_order.assert_called_once()
    if stage == "poll-cleanup":
        assert ddns.update.await_count == 2
        assert "acme-txt-cleanup" in caplog.text


def sensitive_network_failure():
    return httpx.ReadTimeout(MARKER, request=httpx.Request("GET", f"https://fixture.invalid/{MARKER}?token={MARKER}"))


@pytest.mark.anyio
async def test_prefetch_and_fallback_error_wrappers_keep_search_result_without_secret(caplog):
    from app.modules.torrent_streams.service import TorrentStreamsService

    caplog.set_level(logging.DEBUG, logger="app.common.logger")
    provider = SimpleNamespace(find_by_imdb_id=AsyncMock(return_value=([], [])))
    service = TorrentStreamsService(
        db=Mock(), torrent_source_provider_service=cast(Any, provider), torrents_service=Mock(),
        settings_service=cast(Any, SimpleNamespace(get_app_url=lambda:"https://fixture.invalid")),
        preferences_service=cast(Any, SimpleNamespace(get_list=lambda:[])),
    )
    user = SimpleNamespace(attribute_exclusions=[], torrent_seed=None, enable_smart_filter=False, enable_stream_deduplication=False)

    async def prefetch():
        raise sensitive_network_failure()

    task = asyncio.create_task(prefetch())
    streams, errors = await service.find_by_imdb(
        user=cast(Any, user), imdb_id="tt0000001", prefetch_task=task,
        fallback_title=AsyncMock(side_effect=sensitive_network_failure()),
    )
    assert streams == errors == []
    provider.find_by_imdb_id.assert_awaited_once()
    assert "stream-prefetch" in caplog.text
    assert "stream-fallback-title" in caplog.text
    assert "ReadTimeout" in caplog.text
    assert MARKER not in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("stage", ["episode", "static-alias", "dynamic-alias"])
async def test_metadata_mapping_wrappers_do_not_reemit_network_exception(caplog, stage):
    from app.common.schemas.internal import SeriesInfo
    from app.modules.stremio.schemas import ImdbStreamId
    from app.modules.stremio.service import StremioService

    caplog.set_level(logging.DEBUG, logger="app.common.logger")
    resolver = SimpleNamespace(
        get_episode_mappings=AsyncMock(return_value=([], [])),
        get_alternate_imdb_ids=AsyncMock(return_value=[]),
    )
    operation = {"episode":"episode-mapping", "static-alias":"imdb-alias", "dynamic-alias":"dynamic-imdb-alias"}[stage]
    if stage == "episode":
        resolver.get_episode_mappings.side_effect = sensitive_network_failure()
    else:
        resolver.get_alternate_imdb_ids.side_effect = [sensitive_network_failure(), []] if stage == "static-alias" else [[], sensitive_network_failure()]
    service = StremioService(
        torrent_streams_service=cast(Any, SimpleNamespace(find_by_imdb=AsyncMock(return_value=([], [])))),
        settings_service=cast(Any, SimpleNamespace(get_app_url=lambda:"https://fixture.invalid")),
        tvdb_resolver_service=cast(Any, resolver),
    )
    result = await service._get_streams_uncached(
        cast(Any, SimpleNamespace(enable_fallback_subtitles=False)),
        ImdbStreamId(imdb_id="tt0000001", series_info=SeriesInfo(season=1, episode=1)),
    )
    assert result == []
    assert operation in caplog.text
    assert "ReadTimeout" in caplog.text
    assert MARKER not in caplog.text


@pytest.mark.anyio
async def test_tech_enrichment_error_wrapper_does_not_render_remote_data(caplog):
    from app.modules.torrent_streams.service import TorrentStreamsService

    caplog.set_level(logging.DEBUG, logger="app.common.logger")
    service = object.__new__(TorrentStreamsService)
    adapter = SimpleNamespace(fetch_tech_info=AsyncMock(side_effect=sensitive_network_failure()))
    service._indexer_definitions_service = cast(Any, SimpleNamespace(get_by_id=lambda _:adapter))
    await service._enrich_torrent_group(("synthetic-wrapper", "one"), [])
    assert "stream-group-enrichment" in caplog.text
    assert MARKER not in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["sync_ip", "check_ssl_certificate"])
async def test_scheduled_network_wrapper_does_not_attach_sensitive_traceback(monkeypatch, caplog, method):
    from app.modules.network import background_tasks as network_tasks

    service = SimpleNamespace(**{method:AsyncMock(side_effect=sensitive_network_failure())})
    monkeypatch.setattr(network_tasks, "db_session", lambda:nullcontext(object()))
    monkeypatch.setattr(network_tasks, "create_network_service", lambda _:service)
    await (network_tasks.run_network_ip_sync() if method == "sync_ip" else network_tasks.run_check_ssl_certificate())
    assert "scheduled-" in caplog.text
    assert "ReadTimeout" in caplog.text
    assert MARKER not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.anyio
@pytest.mark.parametrize("search", ["t-one", "synthetic-name"])
async def test_catalog_error_wrapper_preserves_empty_result_without_remote_data(caplog, search):
    from app.modules.stremio.catalogs_service import StremioCatalogsService
    from app.modules.stremio.constants import SEARCH_ID
    from app.modules.stremio.enums import MediaType
    from app.modules.stremio.schemas import ParsedExtra

    provider = SimpleNamespace(
        find_by_torrent_id=AsyncMock(side_effect=sensitive_network_failure()),
        find_by_query=AsyncMock(side_effect=sensitive_network_failure()),
    )
    service = StremioCatalogsService(Mock(), cast(Any, provider), Mock())
    response = await service.get_catalog(MediaType.MOVIE, SEARCH_ID, ParsedExtra(search=search))
    assert response.metas == []
    assert "operation=catalog-" in caplog.text
    assert "ReadTimeout" in caplog.text
    assert MARKER not in caplog.text


def test_torznab_item_error_wrapper_does_not_render_source_or_exception(monkeypatch, caplog):
    from app.modules.torznab import service as torznab
    from app.modules.torznab.enums import TorznabCategory

    monkeypatch.setattr(torznab, "build_feed_item", Mock(side_effect=sensitive_network_failure()))
    source = SimpleNamespace(indexer_torrent=SimpleNamespace(torrent_id=MARKER))
    assert torznab.TorznabService._to_feed_items(cast(Any, [source]), TorznabCategory.MOVIE) == []
    assert "operation=torznab-item" in caplog.text
    assert MARKER not in caplog.text
