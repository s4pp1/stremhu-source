"""Private Docker-only synthetic tracker/CDN for G15 wiring.

No outbound requests, real credentials or persisted data. Cookie values and
request headers are never logged; only boolean cookie-scope counters leave it.
"""

import gzip
import json
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from metadata_sizes import make_metadata


BODIES = {
    "small": make_metadata(1 << 30, 256 << 10, 1),
    "many-files": make_metadata(256 << 30, 4 << 20, 1000),
    "large-valid": make_metadata(1 << 40, 1 << 20, 10000),
}
COMPRESSED = gzip.compress(b"x" * (128 << 20), compresslevel=1, mtime=0)
LOCK = threading.Lock()
COUNTERS = Counter()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def body(self, data, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", "application/x-bittorrent")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            with LOCK:
                COUNTERS["closed-early"] += 1

    def do_POST(self):
        if self.path != "/fixture/login":
            self.body(b"", status=404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if size > 4096:
            self.body(b"", status=413)
            return
        self.rfile.read(size)
        with LOCK:
            COUNTERS["login"] += 1
        self.body(b"ok", headers={"Set-Cookie": "fixture-session=valid; Path=/; HttpOnly"})

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/fixture/ready":
            self.body(json.dumps(dict(ready=True, sizes={k: len(v) for k, v in BODIES.items()},
                                      gzip_raw_bytes=len(COMPRESSED), gzip_decoded_bytes=128 << 20)).encode())
            return
        if path == "/fixture/stats":
            with LOCK:
                stats = dict(COUNTERS)
            self.body(json.dumps(stats).encode())
            return
        kind = path.removeprefix("/payload/")
        with LOCK:
            COUNTERS[kind] += 1
            if self.headers.get("Host", "").startswith("cdn.other.invalid") and self.headers.get("Cookie"):
                COUNTERS["foreign-cookie-present"] += 1
        if kind == "login-redirect":
            if "fixture-session=valid" not in self.headers.get("Cookie", ""):
                self.body(b"", 302, {"Location": "/payload/login-required"})
            else:
                self.body(BODIES["small"])
            return
        if kind == "login-required":
            self.body(b"<html>synthetic login required</html>", headers={"X-Fixture-Auth-Required": "1"})
            return
        if kind == "cdn-redirect":
            self.body(b"", 302, {"Location": "http://cdn.other.invalid:8080/payload/small"})
            return
        if kind == "gzip-large":
            self.body(COMPRESSED, headers={"Content-Encoding": "gzip"})
            return
        if kind in {"chunked-large", "drip"}:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-bittorrent")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            block = b"x" * (1024 if kind == "drip" else 65536)
            count = 40 if kind == "drip" else 1024
            try:
                for _ in range(count):
                    self.wfile.write(f"{len(block):x}\r\n".encode() + block + b"\r\n")
                    self.wfile.flush()
                    if kind == "drip":
                        time.sleep(.1)
                self.wfile.write(b"0\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                with LOCK:
                    COUNTERS["closed-early"] += 1
            return
        if kind in BODIES:
            self.body(BODIES[kind])
        else:
            self.body(b"", status=404)


class Server(ThreadingHTTPServer):
    daemon_threads = True


Server(("0.0.0.0", 8080), Handler).serve_forever()
