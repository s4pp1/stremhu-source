"""Synthetic pairing init/link and two-connection race baseline."""

import concurrent.futures
import datetime
import inspect
import itertools
import json
import statistics
import tempfile
import threading
import time
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.common.database import Base
from app.modules.pairings import service as pairing_module
from app.modules.pairings.models import PairingModel
from app.modules.pairings.repository import PairingsRepository
from app.modules.roles.models import RoleModel
from app.modules.users.models import UserModel


with tempfile.TemporaryDirectory() as directory:
    engine = create_engine(f"sqlite:///{Path(directory)/'pairings.db'}", connect_args={"check_same_thread":False,"timeout":1}, hide_parameters=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(RoleModel(id="user",name="Fixture")); db.flush()
        db.add_all([UserModel(id="one",username="one"),UserModel(id="two",username="two")]); db.commit()
    counter = itertools.count()
    modern = "code_factory" in inspect.signature(pairing_module.PairingsService).parameters
    if not modern:
        pairing_module.random.choices = lambda population,k: list(f"{next(counter):04}")
    rows, samples, rebinds = [], [], 0
    for _ in range(100):
        with Session(engine) as db:
            kwargs = {"code_factory":lambda:f"{next(counter):04}"} if modern else {}
            service = pairing_module.PairingsService(PairingsRepository(db),**kwargs)
            started=time.perf_counter_ns()
            pair=service.generate_pairing_codes()
            service.authorize_pairing_code(pair.user_code,db.get(UserModel,"one"))
            try:
                service.authorize_pairing_code(pair.user_code,db.get(UserModel,"two"))
            except HTTPException as error:
                assert error.status_code==409
            db.commit()
            owner=db.scalar(select(PairingModel.user_id).where(PairingModel.user_code==pair.user_code))
            rebinds += owner=="two"
            samples.append((time.perf_counter_ns()-started)/1e6)
    ordered=sorted(samples)
    rows.append(dict(workload="init-link-rebind",concurrency=1,samples_ms=samples,p50_ms=statistics.median(samples),p95_ms=ordered[94],p99_ms=ordered[98],cross_user_rebinds=rebinds,errors=[]))
    barrier=threading.Barrier(2)
    attempts=itertools.count()
    lock=threading.Lock()

    def code():
        with lock:
            index=next(attempts)
        return "0123" if index<2 else f"{1000+index:04}"

    if not modern:
        pairing_module.random.choices=lambda population,k:list(code())

    def init_concurrently():
        with Session(engine) as db:
            repo=PairingsRepository(db)
            method="try_create_unique_pairing" if modern else "find_by_user_code"
            original=getattr(repo,method)
            first=True
            def synchronized(*args,**kwargs):
                nonlocal first
                if modern:
                    if first: first=False; barrier.wait(timeout=2)
                    return original(*args,**kwargs)
                result=original(*args,**kwargs)
                if first: first=False; barrier.wait(timeout=2)
                return result
            setattr(repo,method,synchronized)
            service=pairing_module.PairingsService(repo,**({"code_factory":code} if modern else {}))
            pair=service.generate_pairing_codes(); db.commit(); return pair.user_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        codes=list(executor.map(lambda _:init_concurrently(),range(2)))
    print(json.dumps(dict(fixture="pairing-two-file-db-connections-v1",rows=rows,concurrent_inits=2,distinct_codes=len(set(codes)))))
    engine.dispose()
