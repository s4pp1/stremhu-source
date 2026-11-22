import builtins
import logging
from dataclasses import dataclass

import httpx

SAFE_ACCESS_LOG_FORMAT = "%(m)s %(s)s %(L)s"


@dataclass(frozen=True)
class NetworkErrorSummary:
    kind: str
    status_code: int | None


def network_error_fields(exc: BaseException) -> NetworkErrorSummary:
    """Never stringify exceptions: HTTP errors may embed credentials and bodies."""
    return NetworkErrorSummary(
        kind=type(exc).__name__,
        status_code=exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None,
    )


def safe_endpoint_label(indexer_id: str, operation: str) -> str:
    # Callers supply internal adapter IDs and operation names, never URLs.
    return f"provider={indexer_id} operation={operation}"


def _replace_exception_record(record: logging.LogRecord, summary: NetworkErrorSummary) -> None:
    record.msg = "operation=network-error %s"
    record.args = (summary,)
    record.exc_info = None
    record.exc_text = None
    record.stack_info = None


class SensitiveNetworkLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # HTTPX emits complete request URLs at INFO; httpcore has descendants.
        # Drop these records before formatting, independent of dev/prod level.
        if any(record.name == name or record.name.startswith(name + ".") for name in ("httpx", "httpcore")):
            return False
        candidates: list[BaseException] = []
        if record.exc_info and isinstance(record.exc_info[1], BaseException):
            candidates.append(record.exc_info[1])
        if isinstance(record.msg, BaseException):
            candidates.append(record.msg)
        truncated = False
        arguments = record.args.values() if isinstance(record.args, dict) else record.args
        if arguments:
            for index, value in enumerate(arguments):
                if index == 64:
                    truncated = True
                    break
                if isinstance(value, BaseException):
                    candidates.append(value)
        seen: set[int] = set()
        while candidates and len(seen) < 64:
            error = candidates.pop()
            if id(error) in seen:
                continue
            seen.add(id(error))
            if isinstance(error, httpx.HTTPError) or type(error).__module__.startswith("httpcore."):
                # A generic outer logger may receive a wrapped network error.
                # Replace the entire message too: it may already contain str(e).
                # A traceback can expose URLs, bodies or source locals; retain
                # only the same typed diagnostic fields used by call sites.
                _replace_exception_record(record, network_error_fields(error))
                return True
            if error.__cause__ is not None:
                candidates.append(error.__cause__)
            if error.__context__ is not None:
                candidates.append(error.__context__)
            if isinstance(error, builtins.BaseExceptionGroup):
                truncated = truncated or len(error.exceptions) > 64
                candidates.extend(error.exceptions[:64])
        if candidates or truncated:
            # A bounded inspection must not format an uninspected tail.
            _replace_exception_record(record, NetworkErrorSummary("ExceptionChainLimit", None))
        return True
