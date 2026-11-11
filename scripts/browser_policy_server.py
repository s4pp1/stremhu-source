"""Disposable HTTPS/proxy fixture. No production lifespan or external service.

Only run in the isolated local Docker test network, with synthetic credentials.
The certificate is temporary; browser trust is explicitly overridden for this
cookie/origin test, so this fixture cannot satisfy the native-client G06 gate.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, cast

import httpx
from argon2 import PasswordHasher
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import Depends, HTTPException, Request
from hypercorn.asyncio import serve
from hypercorn.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from app.common import database
from app.config import config
from app.main import app
from app.modules.roles.models import RoleModel
from app.modules.settings.models import SettingModel
from app.modules.settings.dependencies import create_settings_service
from app.modules.stremio.dependencies import get_stremio_service
from app.modules.stremio.service import StremioService
from app.modules.torrent_streams.service import TorrentStreamsService
from app.modules.users.models import UserModel

logical_time = [0.0]


class CandidateOriginPolicy:
    """Exercise the exact helper before any production guard is switched."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and (
            scope["path"] in {"/api/auth/login", "/api/auth/logout", "/api/auth/register"}
            or scope["path"].startswith("/api/me/")
        ):
            from app.common.session_origin import require_browser_origin
            try:
                await asyncio.to_thread(require_browser_origin, Request(scope))
            except HTTPException as error:
                await JSONResponse({"detail":error.detail}, status_code=error.status_code, headers={"Cache-Control":"no-store"})(scope, receive, send)
                return
        await self.application(scope, receive, send)


async def landing(scope, receive, send):
    if scope["type"] == "lifespan":
        await fixture_lifespan(receive, send)
    elif scope["type"] == "http" and scope["path"].startswith("/fixture/"):
        if scope["path"] == "/fixture/next":
            logical_time[0] += 60
        response = PlainTextResponse("ready") if scope["path"] == "/fixture/ready" else HTMLResponse("<!doctype html><html><body>Local synthetic browser fixture</body></html>")
        await response(scope, receive, send)
    else:
        await app(scope, receive, send)


async def proxy(scope, receive, send):
    if scope["type"] == "lifespan":
        await fixture_lifespan(receive, send)
        return
    if scope["type"] != "http":
        return
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body"):
            break
    headers = [(key, value) for key, value in scope["headers"] if key not in {b"host", b"connection", b"transfer-encoding", b"content-length"}]
    headers += [(b"host", b"internal-backend.invalid"), (b"x-forwarded-host", b"proxy.fixture.invalid"), (b"x-forwarded-proto", b"https")]
    target = "http://127.0.0.1:8000" + scope["raw_path"].decode("ascii")
    if scope.get("query_string"):
        target += "?" + scope["query_string"].decode("ascii")
    async with httpx.AsyncClient(trust_env=False) as client:
        upstream = await client.request(scope["method"], target, headers=headers, content=body)
    result = Response(upstream.content, status_code=upstream.status_code)
    result.raw_headers = [(key, value) for key, value in upstream.headers.raw if key.lower() not in {b"connection", b"transfer-encoding"}]
    await result(scope, receive, send)


async def fixture_lifespan(receive, send):
    # Hypercorn also negotiates lifespan with a function ASGI application.
    # Never forward that negotiation into the product's startup/shutdown.
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def main():
    profile = os.environ["CR_BROWSER_PROFILE"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "synthetic browser fixture")])
        names = ["local.fixture.invalid", "proxy.fixture.invalid", "foreign.fixture.invalid"]
        cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1)).not_valid_after(datetime.now(timezone.utc) + timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(host) for host in names]), critical=False).sign(key, hashes.SHA256())
        (root / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (root / "key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        engine = create_engine(f"sqlite:///{root / 'browser.db'}", connect_args={"check_same_thread": False}, hide_parameters=True)
        database.Base.metadata.create_all(engine)
        database.SessionLocal = sessionmaker(bind=engine, autoflush=False)
        from app.common import auth_rate_limit
        auth_rate_limit.auth_rate_limiter = auth_rate_limit.AuthRateLimiter(now=lambda:logical_time[0])
        # Manifest does not use torrent search. Avoid initializing unrelated
        # native Relay/indexer singletons merely to construct that dependency.
        def manifest_service(db: Annotated[Session, Depends(database.get_db, scope="function")]):
            return StremioService(torrent_streams_service=cast(TorrentStreamsService, object()), settings_service=create_settings_service(db))
        app.dependency_overrides[get_stremio_service] = manifest_service
        config.reverse_proxy_domain = "proxy.fixture.invalid" if profile == "proxy" else None
        config.port = 8443
        with Session(engine) as db:
            db.add(RoleModel(id="admin", name="Synthetic admin"))
            db.flush()
            db.add(UserModel(id="one", username="fixture", role_id="admin", api_key="synthetic-browser-key", password_hash=PasswordHasher().hash("synthetic-browser-password")))
            db.add(SettingModel(key="network", value={"mode":"local", "host":"local.fixture.invalid", "ip":"192.0.2.1", "self_signed":True, "fullchain":"synthetic fixture only", "privkey":"synthetic fixture only", "expires_at":4102444800}))
            db.commit()
        if os.environ.get("CR_BROWSER_CANDIDATE") == "true" or os.environ.get("CR_BROWSER_PRODUCTION") == "true":
            config.session_allowed_origins = ["https://alternate.fixture.invalid:8443"]
        if os.environ.get("CR_BROWSER_CANDIDATE") == "true":
            # Candidate-only middleware options, before the production switch.
            from starlette.middleware.sessions import SessionMiddleware

            for middleware in app.user_middleware:
                if middleware.cls is SessionMiddleware:
                    middleware.kwargs.update(https_only=True, same_site="lax")
            application = CandidateOriginPolicy(landing)
        else:
            application = landing
        async def start(application, port, tls):
            settings = Config()
            settings.bind = [f"0.0.0.0:{port}"]
            settings.accesslog = None
            settings.errorlog = None
            if tls:
                settings.certfile = str(root / "cert.pem")
                settings.keyfile = str(root / "key.pem")
            await serve(application, settings, shutdown_trigger=asyncio.Event().wait)
        try:
            if profile == "proxy":
                await asyncio.gather(start(application, 8000, False), start(proxy, 443, True), start(application, 8443, True))
            else:
                await start(application, 8443, True)
        finally:
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
