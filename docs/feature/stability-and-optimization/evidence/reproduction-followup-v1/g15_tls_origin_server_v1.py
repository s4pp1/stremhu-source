"""Private synthetic TLS origin matrix; cookies/headers never logged."""
import json
import ssl
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from metadata_sizes import make_metadata

BODY=make_metadata(1<<30,256<<10,1)
LOCK=threading.Lock()
STATS=defaultdict(lambda:dict(payload_requests=0,cookie_present=0,target_origins=[]))

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def reply(self,body=b'',status=200,headers=None):
        self.send_response(status)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Content-Type','application/x-bittorrent')
        for name,value in (headers or {}).items():self.send_header(name,value)
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        url=urlsplit(self.path)
        case=parse_qs(url.query).get('case',['none'])[0]
        if url.path=='/ready':self.reply(json.dumps(dict(ready=True,body_bytes=len(BODY))).encode());return
        if url.path=='/stats':
            with LOCK:body=json.dumps(dict(STATS)).encode()
            self.reply(body);return
        if url.path=='/set-host':self.reply(b'ok',headers={'Set-Cookie':'fixture-session=valid; Path=/; Secure; HttpOnly'});return
        if url.path=='/set-wide':self.reply(b'ok',headers={'Set-Cookie':'fixture-session=valid; Domain=.fixture.invalid; Path=/; Secure; HttpOnly'});return
        if url.path=='/payload/small':
            scheme='https' if isinstance(self.connection,ssl.SSLSocket) else 'http'
            origin=scheme+'://'+self.headers.get('Host','')
            with LOCK:
                STATS[case]['payload_requests']+=1
                STATS[case]['cookie_present']+=bool(self.headers.get('Cookie'))
                STATS[case]['target_origins'].append(origin)
            self.reply(BODY);return
        target={
            'relative':'/payload/small',
            'same-origin':'https://tracker.fixture.invalid:8443/payload/small',
            'other-port':'https://tracker.fixture.invalid:9443/payload/small',
            'subdomain':'https://cdn.fixture.invalid:8443/payload/small',
            'other-host':'https://cdn.other.invalid:8443/payload/small',
            'downgrade':'http://tracker.fixture.invalid:8080/payload/small',
        }.get(url.path.removeprefix('/redirect/'))
        if target is not None:self.reply(status=302,headers={'Location':target+'?case='+case});return
        self.reply(status=404)

class Server(ThreadingHTTPServer):daemon_threads=True

context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/fixture/pki/cert.pem','/fixture/pki/key.pem')
servers=[]
for port in [8080,8443,9443]:
    server=Server(('0.0.0.0',port),Handler)
    if port!=8080:server.socket=context.wrap_socket(server.socket,server_side=True)
    servers.append(server)
    threading.Thread(target=server.serve_forever,daemon=True).start()
threading.Event().wait()
