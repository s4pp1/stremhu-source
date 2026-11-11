"""Public GZip API compatibility gate before any production compression change."""

import asyncio
import gzip
import hashlib
import importlib.metadata
import json

import httpx
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware


async def main():
    app=FastAPI()
    app.add_middleware(GZipMiddleware,minimum_size=1024,compresslevel=1)

    @app.get("/fixture")
    async def fixture():
        return {"synthetic":"representative JSON "*200}

    rows=[]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="https://fixture.invalid") as client:
        for value in ["identity","gzip","gzip;q=0","gzip;q=0, identity;q=1","br, gzip;q=0.5", "gzip;q=0.1, identity;q=1"]:
            response=await client.send(client.build_request("GET","/fixture",headers={"Accept-Encoding":value}),stream=True)
            try:
                wire=b"".join([chunk async for chunk in response.aiter_raw()])
                encoding=response.headers.get("content-encoding","identity")
                decoded=gzip.decompress(wire) if encoding=="gzip" else wire
                rows.append(dict(accept_encoding=value,status=response.status_code,encoding=encoding,wire_bytes=len(wire),decoded_sha256=hashlib.sha256(decoded).hexdigest(),vary=response.headers.get("vary"),forbidden_gzip_sent="gzip;q=0" in value and "gzip;q=0.5" not in value and "gzip;q=0.1" not in value and encoding=="gzip"))
            finally:await response.aclose()
    print(json.dumps(dict(fixture="g03-public-middleware-encoding-gate-v1",starlette=importlib.metadata.version("starlette"),rows=rows,all_decoded_identical=len({r["decoded_sha256"] for r in rows})==1,forbidden_encoding_count=sum(r["forbidden_gzip_sent"] for r in rows))))


asyncio.run(main())
