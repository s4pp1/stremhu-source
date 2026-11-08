import asyncio
import concurrent.futures

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.common import auth_rate_limit
from app.common.auth_rate_limit import AuthRateLimiter, RatePolicy
from app.main import app


@pytest.fixture
def frozen_limits(monkeypatch):
    limiter = AuthRateLimiter(now=lambda: 0)
    monkeypatch.setattr(auth_rate_limit, "auth_rate_limiter", limiter)
    return limiter


def test_burst_refill_and_retry_after_boundary():
    clock = [0.0]
    limiter = AuthRateLimiter(now=lambda: clock[0])
    policy = RatePolicy("fixture", 10)
    for _ in range(10):
        limiter.admit(((policy, "one"),))
    with pytest.raises(HTTPException) as error:
        limiter.admit(((policy, "one"),))
    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "6"}
    clock[0] = 5.99
    with pytest.raises(HTTPException):
        limiter.admit(((policy, "one"),))
    clock[0] = 6
    limiter.admit(((policy, "one"),))


def test_capacity_never_evicts_a_depleted_identity():
    clock = [0.0]
    limiter = AuthRateLimiter(now=lambda: clock[0])
    policy = RatePolicy("fixture", 1)
    for i in range(4096):
        limiter.admit(((policy, str(i)),))
    for identity in ["new", "0"]:
        with pytest.raises(HTTPException) as error:
            limiter.admit(((policy, identity),))
        assert error.value.status_code == 429
    assert limiter.bucket_count == 4096
    clock[0] = 60
    limiter.admit(((policy, "new"),))
    limiter.admit(((policy, "0"),))
    assert limiter.bucket_count <= 4096


def test_multi_scope_failure_does_not_spend_other_scope_or_allocate_keys():
    limiter = AuthRateLimiter(max_keys=2)
    account, source = RatePolicy("account", 1), RatePolicy("source", 2)
    limiter.admit(((account, "one"),))
    with pytest.raises(HTTPException):
        limiter.admit(((account, "one"), (source, "one")))
    assert limiter.bucket_count == 1
    limiter.admit(((source, "one"),))
    limiter.admit(((source, "one"),))
    with pytest.raises(HTTPException):
        limiter.admit(((source, "one"),))


def test_real_threads_share_one_burst():
    limiter = AuthRateLimiter(now=lambda: 0)
    policy = RatePolicy("fixture", 10)

    def attempt(_):
        try:
            limiter.admit(((policy, "shared"),))
            return 200
        except HTTPException as error:
            return error.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        statuses = list(executor.map(attempt, range(100)))
    assert statuses.count(200) == 10
    assert statuses.count(429) == 90


@pytest.mark.anyio
async def test_cancellation_does_not_refund_an_admitted_token(anyio_backend):
    limiter = AuthRateLimiter(now=lambda: 0)
    policy = RatePolicy("fixture", 1)
    started = asyncio.Event()

    async def admitted_work():
        limiter.admit(((policy, "one"),))
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(admitted_work())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(HTTPException) as error:
        limiter.admit(((policy, "one"),))
    assert error.value.status_code == 429


def test_login_source_limit_ignores_spoofed_forwarded_headers(pairing_engine, frozen_limits):
    client = TestClient(app)
    for i in range(30):
        response = client.post("/api/auth/login", json={"username":f"missing-{i}", "password":"fixture"}, headers={"X-Forwarded-For":str(i), "X-Forwarded-Host":str(i)})
        assert response.status_code == 404
    response = client.post("/api/auth/login", json={"username":"another", "password":"fixture"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "2"
    assert response.headers["Cache-Control"] == "no-store"
    # Denied new accounts cannot fill the key store after the source is limited.
    assert frozen_limits.bucket_count == 31


def test_login_account_limit_survives_transport_changes(pairing_engine, frozen_limits):
    for i in range(10):
        client = TestClient(app, client=(f"192.0.2.{i+1}", 1234))
        response = client.post("/api/auth/login", json={"username":"missing", "password":"fixture"})
        assert response.status_code == 404
    response = TestClient(app, client=("192.0.2.11", 1234)).post("/api/auth/login", json={"username":"missing", "password":"fixture"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "6"


def test_init_and_device_poll_have_separate_scopes(pairing_engine, frozen_limits):
    client = TestClient(app)
    for _ in range(60):
        response = client.post("/api/auth/pair/init")
        assert response.status_code == 200
    response = client.post("/api/auth/pair/init")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "1"
    for _ in range(120):
        response = client.get("/api/auth/pair/status/not-a-real-device")
        assert response.status_code == 404
    response = client.get("/api/auth/pair/status/not-a-real-device")
    assert response.status_code == 429
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/auth/pair/status/other-device").status_code == 404
    assert "not-a-real-device" not in repr(frozen_limits._buckets)


def test_verify_limit_requires_auth_and_is_per_user(pairing_engine, frozen_limits):
    from argon2 import PasswordHasher
    from sqlalchemy.orm import Session

    from app.modules.users.models import UserModel

    with Session(pairing_engine) as db:
        one = db.get(UserModel, "one")
        assert one is not None
        one.password_hash = PasswordHasher().hash("fixture-password")
        db.commit()
    client = TestClient(app)
    assert client.post("/api/auth/pair/verify", json={"userCode":"9999"}).status_code == 401
    assert frozen_limits.bucket_count == 0
    client = TestClient(app, base_url="https://fixture.invalid")
    assert client.post("/api/auth/login", json={"username":"one", "password":"fixture-password"}).status_code == 200
    for _ in range(30):
        response = client.post("/api/auth/pair/verify", json={"userCode":"9999"})
        assert response.status_code == 404
    response = client.post("/api/auth/pair/verify", json={"userCode":"9999"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "2"
