import itertools
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pairings.models import PairingModel
from app.modules.pairings.repository import PairingsRepository
from app.modules.pairings.service import PairingsService
from app.modules.users.models import UserModel


def test_parallel_init_collision_has_two_unique_results(pairing_engine):
    barrier = threading.Barrier(2)
    counter = itertools.count()
    lock = threading.Lock()

    def code():
        with lock:
            index = next(counter)
        return "1234" if index < 2 else f"{2000 + index:04}"

    def initialize():
        with Session(pairing_engine) as db:
            repo = PairingsRepository(db)
            original = repo.try_create_unique_pairing
            first = True

            def synchronized(*args, **kwargs):
                nonlocal first
                if first:
                    first = False
                    barrier.wait(timeout=2)
                return original(*args, **kwargs)

            repo.try_create_unique_pairing = synchronized
            result = PairingsService(repo, code_factory=code).generate_pairing_codes()
            db.commit()
            return result.user_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: initialize(), range(2)))
    assert len(set(results)) == 2


@pytest.mark.parametrize("same_user", [False, True])
def test_parallel_verify_never_overwrites_the_winner(pairing_engine, same_user):
    with Session(pairing_engine) as db:
        pair = PairingsService(PairingsRepository(db)).generate_pairing_codes()
        db.commit()
    barrier = threading.Barrier(2)

    def authorize(identity):
        with Session(pairing_engine) as db:
            user = db.get(UserModel, identity)
            assert user is not None
            barrier.wait(timeout=2)
            try:
                PairingsService(PairingsRepository(db)).authorize_pairing_code(pair.user_code, user)
                db.commit()
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(authorize, ["one", "one" if same_user else "two"]))
    assert sorted(outcomes) == ([200, 200] if same_user else [200, 409])
    with Session(pairing_engine) as db:
        owner = db.scalar(select(PairingModel.user_id).where(PairingModel.user_code == pair.user_code))
        assert owner in ({"one"} if same_user else {"one", "two"})


def test_lock_error_stops_at_first_attempt_with_controlled_503(pairing_engine):
    with pairing_engine.connect() as blocker:
        blocker.exec_driver_sql("BEGIN IMMEDIATE")
        attempts = 0

        def code():
            nonlocal attempts
            attempts += 1
            return "1234"

        try:
            with Session(pairing_engine) as db, pytest.raises(HTTPException) as error:
                PairingsService(PairingsRepository(db), code_factory=code).generate_pairing_codes()
            assert error.value.status_code == 503
            assert attempts == 1
        finally:
            blocker.rollback()
