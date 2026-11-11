import datetime
import uuid

import pytest
from argon2 import PasswordHasher
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.main import app
from app.modules.pairings.models import PairingModel
from app.modules.pairings.repository import PairingsRepository
from app.modules.pairings.service import PairingsService
from app.modules.users.models import UserModel

NOW = datetime.datetime(2026, 1, 1, 12)


def test_bounded_generation_in_a_full_code_space(pairing_engine):
    with Session(pairing_engine) as db:
        db.execute(insert(PairingModel), [{"id": f"pair-{i}", "user_code": f"{i:04}", "device_code": f"fixture-device-{i}", "expires_at": NOW + datetime.timedelta(minutes=1), "created_at": NOW, "status": "pending"} for i in range(10_000)])
        db.commit()
        attempts = 0

        def code():
            nonlocal attempts
            attempts += 1
            return "1234"

        service = PairingsService(PairingsRepository(db), now=lambda: NOW, code_factory=code)
        with pytest.raises(HTTPException) as error:
            service.generate_pairing_codes()
        assert error.value.status_code == 503
        assert error.value.headers == {"Retry-After": "30"}
        assert attempts == 16
        assert db.scalar(select(func.count()).select_from(PairingModel)) == 10_000


def test_link_is_once_idempotent_and_poll_is_retryable(pairing_engine):
    with Session(pairing_engine) as db:
        repo = PairingsRepository(db)
        service = PairingsService(repo, now=lambda: NOW, code_factory=lambda: "1234")
        pair = service.generate_pairing_codes()
        one, two = db.get(UserModel, "one"), db.get(UserModel, "two")
        assert one is not None and two is not None
        assert service.authorize_pairing_code(pair.user_code, one).success
        assert service.authorize_pairing_code(pair.user_code, one).success
        with pytest.raises(HTTPException) as error:
            service.authorize_pairing_code(pair.user_code, two)
        assert error.value.status_code == 409
        for _ in range(2):
            polled = service.poll_pairing_status(pair.device_code)
            matches = polled.token == one.api_key
            assert matches
            assert polled.status == "linked"
        stored = repo.find_by_user_code(pair.user_code)
        assert stored is not None and stored.user_id == "one"


def test_expiry_boundary_poll_verify_and_candidate_reuse(pairing_engine):
    with Session(pairing_engine) as db:
        db.add(PairingModel(user_code="1234", device_code="expired-fixture", expires_at=NOW))
        db.commit()
        service = PairingsService(PairingsRepository(db), now=lambda: NOW, code_factory=lambda: "1234")
        user = db.get(UserModel, "one")
        assert user is not None
        for operation in [lambda: service.poll_pairing_status("expired-fixture"), lambda: service.authorize_pairing_code("1234", user)]:
            with pytest.raises(HTTPException) as error:
                operation()
            assert error.value.status_code == 401
        pair = service.generate_pairing_codes()
        assert pair.expires_at == NOW + datetime.timedelta(minutes=10)
        with pytest.raises(HTTPException) as error:
            service.poll_pairing_status("expired-fixture")
        assert error.value.status_code == 404
        assert service.poll_pairing_status(pair.device_code).status == "pending"


@pytest.mark.parametrize("code", ["", "123", "12345", "12²3", "١٢٣٤", "1" * 5000])
def test_verify_rejects_non_ascii_or_wrong_length(pairing_engine, code):
    with Session(pairing_engine) as db:
        user = db.get(UserModel, "one")
        assert user is not None
        with pytest.raises(HTTPException) as error:
            PairingsService(PairingsRepository(db)).authorize_pairing_code(code, user)
        assert error.value.status_code == 400


def test_device_unique_failure_is_not_retried_and_rolls_back(pairing_engine, monkeypatch):
    sequence = iter([uuid.UUID(int=1), uuid.UUID(int=2), uuid.UUID(int=1), uuid.UUID(int=3)])
    monkeypatch.setattr(uuid, "uuid4", lambda: next(sequence))
    with Session(pairing_engine) as db:
        PairingsService(PairingsRepository(db), now=lambda: NOW, code_factory=lambda: "1234").generate_pairing_codes()
        db.commit()
    with Session(pairing_engine) as db:
        with pytest.raises(HTTPException) as error:
            PairingsService(PairingsRepository(db), now=lambda: NOW, code_factory=lambda: "5678").generate_pairing_codes()
        assert error.value.status_code == 503
        assert db.scalar(select(func.count()).select_from(PairingModel)) == 1


def test_public_device_poll_and_authenticated_verify_http(pairing_engine):
    password = PasswordHasher().hash("fixture-password")
    with Session(pairing_engine) as db:
        for identity in ["one", "two"]:
            user = db.get(UserModel, identity)
            assert user is not None
            user.password_hash = password
        db.commit()
    one, two, device = (TestClient(app, base_url="https://fixture.invalid") for _ in range(3))
    for client, username in [(one, "one"), (two, "two")]:
        assert client.post("/api/auth/login", json={"username":username,"password":"fixture-password"}).status_code == 200
    initialized = device.post("/api/auth/pair/init")
    assert initialized.status_code == 200
    assert initialized.headers["cache-control"] == "no-store"
    pair = initialized.json()
    path = "/api/auth/pair/status/" + pair["deviceCode"]
    assert device.get(path).json()["status"] == "pending"
    assert one.post("/api/auth/pair/verify", json={"userCode":pair["userCode"]}).status_code == 200
    assert one.post("/api/auth/pair/verify", json={"userCode":pair["userCode"]}).status_code == 200
    assert two.post("/api/auth/pair/verify", json={"userCode":pair["userCode"]}).status_code == 409
    for _ in range(2):
        response = device.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["status"] == "linked"
