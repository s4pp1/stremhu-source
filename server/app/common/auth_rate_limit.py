"""Single-process admission. Forwarded headers are never an identity source."""

import hashlib
import math
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class RatePolicy:
    name: str
    capacity: int
    period_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.capacity <= 0 or self.period_seconds <= 0:
            raise ValueError("Invalid admission policy")


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


LOGIN_SOURCE = RatePolicy("login-source", 30)
LOGIN_ACCOUNT = RatePolicy("login-account", 10)
PAIR_INIT = RatePolicy("pair-init-source", 60)
PAIR_VERIFY = RatePolicy("pair-verify-user", 30)
PAIR_STATUS = RatePolicy("pair-status-device", 120)
BOOTSTRAP_SOURCE = RatePolicy("bootstrap-source", 10)


class AuthRateLimiter:
    """Atomic multi-scope token consumption, with no eviction of depleted keys.

    Only fully refilled buckets may be forgotten: recreating them cannot grant
    additional tokens. At capacity, new identities receive 429 until space is
    available. All values retained here are policies, hashes and scalar state.
    """

    def __init__(self, *, now: Callable[[], float] = time.monotonic, max_keys: int = 4096):
        if max_keys <= 0:
            raise ValueError("Invalid admission capacity")
        self._now = now
        self._max_keys = max_keys
        self._lock = threading.Lock()
        self._buckets: dict[tuple[RatePolicy, str], _Bucket] = {}

    @property
    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    @staticmethod
    def _tokens(policy: RatePolicy, bucket: _Bucket, now: float) -> float:
        return min(policy.capacity, bucket.tokens + max(0.0, now - bucket.updated_at) * policy.capacity / policy.period_seconds)

    @staticmethod
    def _limited(retry_seconds: float) -> HTTPException:
        return HTTPException(status_code=429, detail="Túl sok hitelesítési kérés. Próbáld újra később.", headers={"Retry-After": str(max(1, math.ceil(retry_seconds)))})

    def admit(self, rules: Sequence[tuple[RatePolicy, str]]) -> None:
        keys = {(policy, hashlib.sha256(identity.encode("utf-8")).hexdigest()) for policy, identity in rules}
        with self._lock:
            now = self._now()
            available = {key: self._tokens(key[0], self._buckets[key], now) if key in self._buckets else float(key[0].capacity) for key in keys}
            waits = [(1 - tokens) * key[0].period_seconds / key[0].capacity for key, tokens in available.items() if tokens < 1]
            if waits:
                raise self._limited(max(waits))
            missing = keys - self._buckets.keys()
            if len(self._buckets) + len(missing) > self._max_keys:
                for key, bucket in list(self._buckets.items()):
                    if key not in keys and self._tokens(key[0], bucket, now) >= key[0].capacity:
                        del self._buckets[key]
                if len(self._buckets) + len(missing) > self._max_keys:
                    retry = min(((policy.capacity - self._tokens(policy, bucket, now)) * policy.period_seconds / policy.capacity for (policy, _), bucket in self._buckets.items()), default=1.0)
                    raise self._limited(retry)
            for key, tokens in available.items():
                self._buckets[key] = _Bucket(tokens - 1, now)


auth_rate_limiter = AuthRateLimiter()


def transport_peer(request: Request) -> str:
    return request.client.host if request.client else "missing-transport-peer"


def admit_login(request: Request, username: str) -> None:
    auth_rate_limiter.admit(((LOGIN_SOURCE, transport_peer(request)), (LOGIN_ACCOUNT, username.casefold())))


def admit_pair_init(request: Request) -> None:
    auth_rate_limiter.admit(((PAIR_INIT, transport_peer(request)),))


def admit_pair_verify(user_id: str) -> None:
    auth_rate_limiter.admit(((PAIR_VERIFY, user_id),))


def admit_pair_status(device_code: str) -> None:
    auth_rate_limiter.admit(((PAIR_STATUS, device_code),))


def admit_bootstrap(request: Request) -> None:
    auth_rate_limiter.admit(((BOOTSTRAP_SOURCE, transport_peer(request)),))
