"""Origin checks for session mutations; independent from public API-key CORS."""

import asyncio
import threading
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from app.common.database import isolated_db_session
from app.common.validators import normalize_browser_origin
from app.config import config
from app.modules.settings.dependencies import create_settings_service
from app.modules.stremio.cache import stream_cache_state

Origin = tuple[str, str, int]
PolicyKey = tuple[int, int, str | None, int, tuple[str, ...]]
_cache_lock = threading.Lock()
_local_epoch = 0
_origin_cache: tuple[PolicyKey, frozenset[Origin]] | None = None


def clear_origin_cache() -> None:
    global _origin_cache, _local_epoch
    with _cache_lock:
        _local_epoch += 1
        _origin_cache = None


def _policy_key() -> PolicyKey:
    global_epoch = stream_cache_state.global_epoch
    with _cache_lock:
        local_epoch = _local_epoch
    return local_epoch, global_epoch, config.reverse_proxy_domain, config.port, tuple(config.session_allowed_origins)


def _denied() -> HTTPException:
    return HTTPException(status_code=403, detail="A böngészős kérés forrása nem engedélyezett.")


def _request_origin(request: Request) -> tuple[str, str, int] | None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise _denied()
    origins = request.headers.getlist("origin")
    if not origins:
        # Native JSON clients need not synthesize browser headers.
        return None
    if len(origins) != 1:
        raise _denied()
    try:
        return normalize_browser_origin(origins[0])
    except ValueError:
        raise _denied() from None


def _configured_origins() -> set[tuple[str, str, int]]:
    with isolated_db_session() as db:
        app_url = create_settings_service(db).get_app_url()
    # A configured deployment URL may have a base path; an Origin may not.
    parsed = urlsplit(app_url)
    canonical = f"{parsed.scheme}://{parsed.netloc}"
    return {normalize_browser_origin(canonical), *(normalize_browser_origin(value) for value in config.session_allowed_origins)}


def _cached_origins(key: PolicyKey) -> frozenset[Origin] | None:
    with _cache_lock:
        if _origin_cache is not None and _origin_cache[0] == key:
            return _origin_cache[1]
    return None


def _trusted_origins() -> frozenset[Origin]:
    global _origin_cache
    key = _policy_key()
    cached = _cached_origins(key)
    if cached is not None:
        return cached
    # A miss has its own short worker-owned Session, with no lock held.
    allowed = frozenset(_configured_origins())
    if _policy_key() == key:
        with _cache_lock:
            # Do not let an older in-flight load displace a newer generation.
            if _origin_cache is None or _origin_cache[0][:2] <= key[:2]:
                _origin_cache = key, allowed
    return allowed


def require_browser_origin(request: Request) -> None:
    origin = _request_origin(request)
    if origin is None:
        return
    try:
        allowed = _trusted_origins()
    except Exception:
        # No guessed Host/forwarded fallback, and no settings/secrets in errors.
        raise HTTPException(status_code=503, detail="A böngészős hitelesítési policy átmenetileg nem elérhető.") from None
    if origin not in allowed:
        raise _denied()


async def browser_origin_dependency(request: Request) -> None:
    """Async route dependency: a warm lookup needs neither DB nor a worker hop."""
    origin = _request_origin(request)
    if origin is None:
        return
    allowed = _cached_origins(_policy_key())
    if allowed is None:
        work = asyncio.create_task(asyncio.to_thread(_trusted_origins))
        cancelled = False
        while not work.done():
            try:
                await asyncio.shield(work)
            except asyncio.CancelledError:
                if work.cancelled():
                    raise
                cancelled = True
            except Exception:
                break
        if cancelled:
            if not work.cancelled():
                work.exception()
            raise asyncio.CancelledError
        try:
            allowed = work.result()
        except Exception:
            raise HTTPException(status_code=503, detail="A böngészős hitelesítési policy átmenetileg nem elérhető.") from None
    if origin not in allowed:
        raise _denied()
