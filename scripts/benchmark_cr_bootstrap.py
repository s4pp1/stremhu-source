"""Ten real first-admin HTTP calls, synchronized at password hashing.

Only a new file DB and synthetic users are used. Password hashes/cookies/keys
are never emitted. The real hashing work runs outside the measured writer lock.
"""

import concurrent.futures
import json
import tempfile
import threading
import time
from pathlib import Path

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.common import database
from app.common.database import Base
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.users.models import UserModel


with tempfile.TemporaryDirectory() as directory:
    engine = create_engine(f"sqlite:///{Path(directory) / 'bootstrap.db'}", connect_args={"check_same_thread": False, "timeout": 2}, hide_parameters=True)
    Base.metadata.create_all(engine)
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
    with Session(engine) as db:
        db.add(RoleModel(id="admin", name="Fixture admin")); db.commit()
    barrier = threading.Barrier(10)
    original_hash = PasswordHasher.hash
    hash_samples = []
    hash_lock = threading.Lock()

    def synchronized_hash(self, password, *args, **kwargs):
        barrier.wait(timeout=10)
        start = time.perf_counter_ns()
        result = original_hash(self, password, *args, **kwargs)
        with hash_lock:
            hash_samples.append((time.perf_counter_ns()-start)/1e6)
        return result

    PasswordHasher.hash = synchronized_hash

    def call(index):
        started = time.perf_counter_ns()
        client = TestClient(app, raise_server_exceptions=False, base_url="https://fixture.invalid")
        response = client.post("/api/auth/register", json={"username":f"fixture-{index}", "password":"synthetic-fixture-password"})
        return dict(status=response.status_code, milliseconds=(time.perf_counter_ns()-started)/1e6, issued_session="stremhu.source=" in response.headers.get("set-cookie", ""))

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            outcomes = list(executor.map(call, range(10)))
    finally:
        PasswordHasher.hash = original_hash
    with Session(engine) as db:
        users = db.scalar(select(func.count()).select_from(UserModel))
        marker = db.get(SettingModel, "auth_bootstrap_complete") is not None
    print(json.dumps(dict(fixture="ten-way-real-http-bootstrap-v1", outcomes=outcomes, committed_users=users, bootstrap_marker=marker, hash_samples_ms=hash_samples)))
    engine.dispose()
