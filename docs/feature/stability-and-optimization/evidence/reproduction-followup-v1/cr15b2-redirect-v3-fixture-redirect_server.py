"""Private Docker-only fixture for the packet 26b functional gate (v3).

One server under three names: tracker.fixture.invalid (the tracker), dl.tracker.fixture.invalid
(its subdomain) and cdn.other.invalid (a foreign host). Routes:
- /redirect-giant: 302 to /final with a 64 MiB chunked body; counts body bytes written.
- /redirect-sub: 302 to the subdomain's /final; /redirect-foreign: 302 to the foreign host's /final.
- /final: one natively valid metadata-only .torrent; requests counted per Host name.
No outbound traffic.
"""

import json
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from metadata_sizes import make_metadata

FINAL = make_metadata(1 << 30, 256 << 10, 1)
CHUNK = 64 << 10
REDIRECT_BODY = 64 << 20
LOCK = threading.Lock()
COUNTERS = Counter()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def plain(self, data, content_type="application/json", status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        host = self.headers.get("Host", "").split(":")[0]
        if self.path == "/fixture/ready":
            self.plain(json.dumps({"ready": True}).encode())
            return
        if self.path == "/fixture/stats":
            with LOCK:
                payload = dict(COUNTERS)
            self.plain(json.dumps(payload).encode())
            return
        if self.path == "/final":
            with LOCK:
                COUNTERS[f"final@{host}"] += 1
            self.plain(FINAL, "application/x-bittorrent")
            return
        if self.path == "/redirect-sub":
            self.plain(b"", "text/html", 302, {"Location": "http://dl.tracker.fixture.invalid:8080/final"})
            return
        if self.path == "/redirect-foreign":
            self.plain(b"", "text/html", 302, {"Location": "http://cdn.other.invalid:8080/final"})
            return
        if self.path == "/redirect-giant":
            with LOCK:
                COUNTERS["redirect"] += 1
            self.send_response(302)
            self.send_header("Location", "/final")
            self.send_header("Content-Type", "text/html")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            sent = 0
            try:
                block = b"r" * CHUNK
                while sent < REDIRECT_BODY:
                    self.wfile.write(b"%x\r\n%s\r\n" % (CHUNK, block))
                    sent += CHUNK
                self.wfile.write(b"0\r\n\r\n")
                complete = True
            except (BrokenPipeError, ConnectionResetError):
                complete = False
                self.close_connection = True
            with LOCK:
                COUNTERS["redirect-body-bytes"] += sent
                COUNTERS["redirect-body-complete" if complete else "redirect-body-closed-early"] += 1
            return
        self.plain(b"", "text/plain", 404)


class Server(ThreadingHTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    Server(("0.0.0.0", 8080), Handler).serve_forever()
