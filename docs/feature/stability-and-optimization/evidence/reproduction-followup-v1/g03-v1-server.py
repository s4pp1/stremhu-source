"""G03 v1 server fixture. Real Stremio Pydantic response models (frozen aaa9ee5 overlay) served by FastAPI routes with the
same response_model/serialization as the production routes, under Hypercorn (production run() defaults, 1 worker).
Upstream tracker/metadata cost is stubbed constant: model instances are prebuilt deterministically (seeded); per-request
serialization is real. Variants are mounted side by side: /identity (no compression) and /gzip{1,4,6} (Starlette
GZipMiddleware, minimum_size=1; thresholds are derived from per-payload identity size, see protocol)."""
import os
import random
import resource
import time
import uuid

from fastapi import FastAPI
from itsdangerous import URLSafeSerializer
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.modules.stremio.enums import ContentType
from app.modules.stremio.schemas import (BehaviorHints, MetaDetail, MetaLink, MetaPreview, MetaResponse, MetaVideo,
                                         StremioCatalogResponse, StremioStream, StremioStreams, StremioSubtitle)

APP_URL = 'http://192.0.2.10:7070'  # RFC 5737 documentation address; realistic length only
SEED = 20261107
rng = random.Random(SEED)
ser = URLSafeSerializer('g03-fixture-not-a-secret-' + 'x' * 40, salt='stream-token')
API_KEY = str(uuid.UUID(int=rng.getrandbits(128)))
WORDS = ['Shadow', 'River', 'Empire', 'Last', 'Night', 'Kingdom', 'Silent', 'Storm', 'Garden', 'Winter', 'Code', 'Iron', 'Glass',
         'Echo', 'Harbor', 'Crown', 'Wild', 'Signal', 'Paper', 'Moon', 'Velvet', 'Frontier', 'Atlas', 'Hidden']
RES = [('2160p', '4K'), ('1080p', 'FHD'), ('720p', 'HD')]
SRC = ['BluRay', 'WEB-DL', 'WEBRip', 'UHD.BluRay', 'HDTV', 'REMUX']
CODEC = ['x265', 'x264', 'HEVC', 'AVC', 'AV1']
AUDIO = [('DTS-HD.MA.7.1', 'DTS-HD MA', '7.1'), ('TrueHD.Atmos.7.1', 'TrueHD', 'Atmos'), ('DDP5.1', 'DD+', '5.1'), ('AAC2.0', 'AAC', '2.0'),
         ('AC3.5.1', 'DD', '5.1')]
GROUPS = ['FLUX', 'NTb', 'SPARKS', 'HUNTEAM', 'PTer', 'playHD', 'TOMMY', 'RARBG', 'GOSSIP', 'Magyar.HUN']
INDEXERS = ['nCore', 'iTorrent', 'BitHUmen', 'MagyarTorrent']
LANGS = [('hun', '\U0001f1ed\U0001f1fa HUN'), ('eng', '\U0001f1ec\U0001f1e7 ENG'), ('jap', '\U0001f1ef\U0001f1f5 JAP'),
         ('ger', '\U0001f1e9\U0001f1ea GER')]


def title(k):
    return '.'.join(rng.sample(WORDS, k))


def stream(series):
    res, res_label = rng.choice(RES)
    src, codec = rng.choice(SRC), rng.choice(CODEC)
    a_tag, a_label, a_ch = rng.choice(AUDIO)
    base = title(rng.randint(2, 4))
    ep = f'.S0{rng.randint(1, 5)}E{rng.randint(1, 24):02d}' if series else ''
    year = rng.randint(1990, 2026)
    group = rng.choice(GROUPS)
    hdr = rng.choice(['', '.HDR', '.DV', '.HDR10Plus', '']) if res == '2160p' else ''
    file_name = f'{base}{ep}.{year}.{res}.{src}{hdr}.{codec}.{a_tag}-{group}.mkv'
    size = rng.randint(700, 80000) * 1024 * 1024
    torrent_id = str(rng.randint(100000, 3999999))
    indexer = rng.choice(INDEXERS)
    tok = ser.dumps(dict(indexer_id=indexer.lower(), torrent_id=torrent_id, file_index=rng.randint(0, 30),
                         playback_id=str(uuid.UUID(int=rng.getrandbits(128))), imdb_id=f'tt{rng.randint(100000, 9999999):07d}',
                         series_info=dict(season=1, episode=rng.randint(1, 24)) if series else None))
    langs = rng.sample(LANGS, rng.randint(1, 3))
    has_hun_sub = rng.random() < 0.35
    subs = None
    if has_hun_sub:
        subs = []
        for k in range(rng.randint(1, 3)):
            stoken = ser.dumps(dict(indexer_id=indexer.lower(), torrent_id=torrent_id, file_index=40 + k,
                                    playback_id=str(uuid.UUID(int=rng.getrandbits(128)))))
            subs.append(StremioSubtitle(id=f'{torrent_id}-{40 + k}', url=f'{APP_URL}/api/{API_KEY}/subtitles/{stoken}/{base}.{k}.hun.srt',
                                        lang='hun', label=f'Magyar {k + 1}'))
    seeders = rng.randint(0, 900)
    first = ' | '.join([f'\U0001f9f2 {indexer}', f'\U0001f465 {seeders}', f'\U0001f4be {size / 2 ** 30:.2f} GiB'])
    second = ' | '.join([', '.join(x[1] for x in langs)] + (['\U0001f4ac \U0001f1ed\U0001f1fa Felirat'] if has_hun_sub else [])
                        + [f'\U0001f50a {a_label}', a_ch])
    third = ' | '.join([src.replace('.', ' '), codec])
    persisted = rng.random() < 0.1
    lines = (['⚡ Helyben tárolva (Azonnali lejátszás)'] if persisted else []) + (
        [f'\U0001f4c1 {file_name}'] if series else []) + [first, second, third]
    name = ' | '.join((['⚡ Letöltve'] if persisted else []) + [res_label + (f' | {hdr[1:]}' if hdr else '')])
    return StremioStream(name=name, description='\n'.join(lines), url=f'{APP_URL}/api/{API_KEY}/stream/{tok}', subtitles=subs,
                         behavior_hints=BehaviorHints(filename=f'{base}{ep}.{year}.{res}.{".".join(x[0] for x in langs)}.mkv',
                                                      binge_group=f'{indexer.lower()}-{torrent_id}', video_size=size))


def overview():
    return ' '.join(rng.choice(WORDS).lower() for _ in range(rng.randint(25, 45))).capitalize() + '.'


STREAM_COUNTS = [0, 1, 10, 40, 200]
STREAMS = {n: StremioStreams(streams=[stream(series=(n == 40 and i % 2 == 0)) for i in range(n)]) for n in STREAM_COUNTS}
imdb = f'tt{rng.randint(100000, 9999999):07d}'
META = MetaResponse(meta=MetaDetail(
    id=f'stremhu:ncore:{rng.randint(100000, 3999999)}', imdb_id=imdb, type=ContentType.SERIES, name=title(3).replace('.', ' '),
    poster=f'https://images.metahub.space/poster/medium/{imdb}/img', background=f'https://images.metahub.space/background/medium/{imdb}/img',
    logo=f'https://images.metahub.space/logo/medium/{imdb}/img', description=overview() + ' ' + overview(), imdb_rating='7.9',
    release_info='2019-2024', genres=['Drama', 'Crime', 'Thriller'], cast=[title(2).replace('.', ' ') for _ in range(8)],
    director=[title(2).replace('.', ' ')], links=[MetaLink(name=g, category='Genres', url=f'stremio:///discover/{g}') for g in ['Drama', 'Crime']],
    released='2019-03-01T00:00:00.000Z', year='2019-2024', runtime='52 min', language='English', country='USA',
    videos=[MetaVideo(id=f'{imdb}:{s}:{e}', title=title(3).replace('.', ' '), released=f'20{19 + s}-0{1 + e % 9}-1{e % 9}T00:00:00.000Z',
                      thumbnail=f'https://episodes.metahub.space/{imdb}/{s}/{e}/w780.jpg', episode=e, season=s, overview=overview())
            for s in range(1, 6) for e in range(1, 11)]))


def preview():
    m = f'tt{rng.randint(100000, 9999999):07d}'
    return MetaPreview(id=f'stremhu:ncore:{rng.randint(100000, 3999999)}', imdb_id=m, type=ContentType.MOVIE, name=title(3).replace('.', ' '),
                       poster=f'https://images.metahub.space/poster/medium/{m}/img', imdb_rating=f'{rng.uniform(4, 9):.1f}')


CATALOG = {200: StremioCatalogResponse(metas=[preview() for _ in range(200)])}


def make_api():
    api = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @api.get('/streams/{n}', response_model=StremioStreams)
    async def streams(n: int) -> StremioStreams:
        return STREAMS[n]

    @api.get('/meta', response_model=MetaResponse)
    async def meta() -> MetaResponse:
        return META

    @api.get('/catalog/{n}', response_model=StremioCatalogResponse)
    async def catalog(n: int) -> StremioCatalogResponse:
        return CATALOG[n]
    return api


def status_json():
    rss_anon = 0
    with open('/proc/self/status') as f:
        for line in f:
            if line.startswith('RssAnon:'):
                rss_anon = int(line.split()[1]) * 1024
    return dict(cpu_s=time.process_time(), maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, rss_anon_bytes=rss_anon,
                pid=os.getpid())


async def stats(request):
    return JSONResponse(status_json())

app = Starlette(routes=[Route('/__stats', stats), Mount('/identity', app=make_api())] + [
    Mount(f'/gzip{level}', app=GZipMiddleware(make_api(), minimum_size=1, compresslevel=level)) for level in (1, 4, 6)])

if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.run import run
    cfg = Config()
    cfg.application_path = 'server:app'
    cfg.bind = ['0.0.0.0:8080']
    run(cfg)
