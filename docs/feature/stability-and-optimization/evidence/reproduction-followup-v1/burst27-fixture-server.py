"""Private Docker-only synthetic tracker for the packet 27 burst input (descriptive).

Search pages return a fixed, deterministic candidate list per IMDb key. Downloads
serve natively valid, metadata-only .torrent bodies with a fixed time-to-first-byte
and a fixed per-connection rate. No outbound requests, credentials or persistence.
"""

import json
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import libtorrent

from metadata_sizes import make_metadata

K = 40
SEARCH_DELAY = 0.300
TTFB = 0.080
RATE = 8_000_000
CHUNK = 64 << 10
PLACEHOLDER = b"burst-tt0000000-000"
# (logical bytes, piece bytes, files): metadata-only profiles, sizes ~51 KB .. ~21 MB.
PROFILES = {
    "movie": (10 << 30, 4 << 20, 1),
    "pack": (40 << 30, 8 << 20, 24),
    "remux": (80 << 30, 4 << 20, 1),
    "season-box": (256 << 30, 4 << 20, 1000),
    "giant-valid": (1 << 40, 1 << 20, 10000),
}


def profile_for(mix: str, index: int) -> str:
    if mix == "heavy" and index % 8 == 0:
        return "giant-valid"
    if index == 0:
        return "season-box"
    if index <= 5:
        return "remux"
    if index <= 15:
        return "pack"
    return "movie"


def template(profile: str) -> bytes:
    total, piece, files = PROFILES[profile]
    body = make_metadata(total, piece, files)
    marker = b"23:synthetic-metadata-only"
    assert body.count(marker) == 1
    body = body.replace(marker, b"%d:%s" % (len(PLACEHOLDER), PLACEHOLDER))
    assert body.count(PLACEHOLDER) == 1
    return body


TEMPLATES = {name: template(name) for name in PROFILES}
SIZES = {name: len(body) for name, body in TEMPLATES.items()}
for name, body in TEMPLATES.items():
    parsed = libtorrent.torrent_info(body)
    assert parsed.total_size() == PROFILES[name][0] and parsed.num_files() == PROFILES[name][2]
    del parsed
LOCK = threading.Lock()
COUNTERS = Counter()
STATE = {"downloads_now": 0, "downloads_peak": 0, "connections_now": 0, "connections_peak": 0}


def unique_name(imdb: str, index: int) -> bytes:
    name = f"burst-{imdb}-{index:03d}".encode()
    if len(name) != len(PLACEHOLDER):
        raise ValueError("unexpected key length")
    return name


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        with LOCK:
            STATE["connections_now"] += 1
            STATE["connections_peak"] = max(STATE["connections_peak"], STATE["connections_now"])

    def finish(self):
        try:
            super().finish()
        finally:
            with LOCK:
                STATE["connections_now"] -= 1

    def send(self, data: bytes, content_type: str, status: int = 200, paced: bool = False):
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", content_type)
        self.end_headers()
        try:
            if not paced:
                self.wfile.write(data)
                return
            started = time.monotonic()
            for offset in range(0, len(data), CHUNK):
                self.wfile.write(data[offset:offset + CHUNK])
                due = started + (offset + CHUNK) / RATE
                delay = due - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
        except (BrokenPipeError, ConnectionResetError):
            with LOCK:
                COUNTERS["closed-early"] += 1

    def do_GET(self):
        url = urlsplit(self.path)
        parts = url.path.strip("/").split("/")
        if url.path == "/fixture/ready":
            self.send(json.dumps({"ready": True}).encode(), "application/json")
            return
        if url.path == "/fixture/stats":
            with LOCK:
                payload = dict(counters=dict(COUNTERS), **STATE, sizes=SIZES)
            self.send(json.dumps(payload).encode(), "application/json")
            return
        if url.path == "/search":
            query = parse_qs(url.query)
            imdb, mix = query["imdb"][0], query["mix"][0]
            time.sleep(SEARCH_DELAY)
            torrents = [dict(torrent_id=f"{imdb}-{index:03d}", download_url=f"/download/{mix}/{imdb}/{index}",
                             imdb_id=imdb, seeders=100 - index) for index in range(K)]
            with LOCK:
                COUNTERS["search"] += 1
            self.send(json.dumps({"torrents": torrents, "next_page": None}).encode(), "application/json")
            return
        if len(parts) == 4 and parts[0] == "download":
            _, mix, imdb, raw_index = parts
            index = int(raw_index)
            profile = profile_for(mix, index)
            body = TEMPLATES[profile].replace(PLACEHOLDER, unique_name(imdb, index), 1)
            with LOCK:
                COUNTERS["download"] += 1
                COUNTERS["download-bytes"] += len(body)
                STATE["downloads_now"] += 1
                STATE["downloads_peak"] = max(STATE["downloads_peak"], STATE["downloads_now"])
            try:
                time.sleep(TTFB)
                self.send(body, "application/x-bittorrent", paced=True)
            finally:
                with LOCK:
                    STATE["downloads_now"] -= 1
            return
        self.send(b"", "text/plain", status=404)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 256


if __name__ == "__main__":
    Server(("0.0.0.0", 8080), Handler).serve_forever()
