import builtins
import io
import logging
import traceback
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

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
async def test_real_hypercorn_access_formatter_has_no_request_target(monkeypatch, status_code):
    from app import run as run_module
    from app.modules.settings.enums import NetworkModeEnum

    captured: list[HypercornConfig] = []
    monkeypatch.setattr(run_module, "ensure_default_settings", lambda: None)
    monkeypatch.setattr(
        run_module,
        "ensure_network_settings",
        lambda: SimpleNamespace(
            network_settings=SimpleNamespace(mode=NetworkModeEnum.MANUAL, host="fixture.invalid"),
            cert_path=None,
            key_path=None,
        ),
    )
    monkeypatch.setattr(run_module, "run", lambda cfg: captured.append(cfg))
    run_module.start_server()
    assert len(captured) == 1
    configuration = captured[0]
    assert configuration.access_log_format == SAFE_ACCESS_LOG_FORMAT

    output = io.StringIO()
    handler = logging.StreamHandler(output)
    access = logging.Logger("fixture-access", level=logging.INFO)
    access.addHandler(handler)
    configuration.accesslog = access
    log = HypercornLogger(configuration)
    scope = dict(
        type="http",
        method="GET",
        path=f"/api/{MARKER}/stream/{MARKER}",
        raw_path=b"/",
        query_string=f"key={MARKER}".encode(),
        headers=[(b"cookie", MARKER.encode())],
        http_version="1.1",
        scheme="https",
        server=("fixture.invalid", 443),
        client=("192.0.2.1", 1234),
    )
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
        error = builtins.ExceptionGroup(MARKER, [repeated] * 64 + [cast(Exception, error)])
    if shape == "large-args":
        log.error("%s " * 65, *(["ordinary"] * 64 + [error]))
    else:
        log.error("operation failed", exc_info=(type(error), error, None))
    assert MARKER not in output.getvalue()
    assert "ExceptionChainLimit" in output.getvalue()


def sensitive_network_failure():
    return httpx.ReadTimeout(MARKER, request=httpx.Request("GET", f"https://fixture.invalid/{MARKER}?token={MARKER}"))


def test_torznab_item_error_wrapper_does_not_render_source_or_exception(monkeypatch, caplog):
    from app.modules.torznab import service as torznab
    from app.modules.torznab.enums import TorznabCategory

    monkeypatch.setattr(torznab, "build_feed_item", Mock(side_effect=sensitive_network_failure()))
    source = SimpleNamespace(indexer_torrent=SimpleNamespace(torrent_id=MARKER))
    assert torznab.TorznabService._to_feed_items(cast(Any, [source]), TorznabCategory.MOVIE) == []
    assert "operation=torznab-item" in caplog.text
    assert MARKER not in caplog.text
