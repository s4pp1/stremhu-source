"""Local-only controlled slow body; never logs URLs or request headers."""
import json
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from metadata_sizes import make_metadata

BODY = make_metadata(1 << 30, 256 << 10, 1)
LOCK = threading.Lock()
STATS = defaultdict(lambda: dict(started=0, active=0, completed=0, closed_early=0, sent_bytes=0))


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def small(self, body):
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/stats':
            with LOCK:
                body = json.dumps(dict(STATS)).encode()
            self.small(body)
            return
        if url.path == '/small':
            self.small(BODY)
            return
        if url.path != '/drip':
            self.send_error(404)
            return
        case = parse_qs(url.query)['case'][0]
        with LOCK:
            STATS[case]['started'] += 1
            STATS[case]['active'] += 1
        self.send_response(200)
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()
        block = b'x' * 1024
        try:
            for _ in range(50):
                self.wfile.write(b'400\r\n' + block + b'\r\n')
                self.wfile.flush()
                with LOCK:
                    STATS[case]['sent_bytes'] += len(block)
                time.sleep(.5)
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
            with LOCK:
                STATS[case]['completed'] += 1
        except (BrokenPipeError, ConnectionResetError):
            with LOCK:
                STATS[case]['closed_early'] += 1
        finally:
            with LOCK:
                STATS[case]['active'] -= 1


class Server(ThreadingHTTPServer):
    daemon_threads = True


Server(('0.0.0.0', 8080), Handler).serve_forever()
