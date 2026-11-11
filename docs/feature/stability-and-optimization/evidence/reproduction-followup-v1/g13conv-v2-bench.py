"""G13-convert v2 (candidate gate) fixture: identical fixtures/heartbeat to v1; the measured step is the endpoint conversion step of the mounted source (await ass_to_vtt_cooperative if present, else the synchronous ass_to_vtt). v1 docstring follows.
G13-convert v1 fixture: event-loop stall of the production ASS->VTT path (decode + ass_to_vtt), run exactly as the
subtitle endpoint does (synchronously inside the async handler). Deterministic synthetic ASS fixtures:
typical (~120 KB dialogue), heavy (~3 MB karaoke/sign typesetting), limit (just under the 8 MiB subtitle_max_source_bytes),
and a cp1250 typical file (fallback decode path). Per fixture: warmup, then timed inline runs with a 1 ms heartbeat
task measuring the largest loop gap; informative to_thread runs show GIL-sharing behaviour of a thread offload.
argv: label output.json [--smoke]"""
import asyncio
import hashlib
import json
import random
import statistics
import sys
import time

SMOKE = '--smoke' in sys.argv
LIMIT = 8 * 1024 * 1024
rng = random.Random(1307)
HEADER = ('[Script Info]\nTitle: G13 fixture\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n'
          'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
          'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
          'Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2.5,1,2,60,60,40,1\n'
          'Style: Sign,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,10,10,10,1\n\n'
          '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
WORDS = ['mondom', 'neked', 'hogy', 'ez', 'nem', 'lehet', 'igaz', 'gyere', 'velem', 'most', 'azonnal', 'csillag', 'vihar', 'kard', 'tenger',
         'barátom', 'soha', 'mindig', 'holnap', 'éjszaka', 'fény', 'árnyék', 'őrző', 'sárkány']


def ts(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def sentence(n):
    return ' '.join(rng.choice(WORDS) for _ in range(n)).capitalize()


def dialogue(t, heavy):
    start, end = ts(t), ts(t + rng.uniform(1.0, 4.0))
    if not heavy or rng.random() < 0.3:
        text = sentence(rng.randint(3, 9)) + (r'\N' + sentence(rng.randint(2, 6)) if rng.random() < 0.4 else '')
        if rng.random() < 0.15:
            text = r'{\i1}' + text + r'{\i0}'
        return f'Dialogue: 0,{start},{end},Default,,0,0,0,,{text}'
    kind = rng.random()
    if kind < 0.5:  # karaoke line: per-syllable override tags
        syl = ''.join(f'{{\\k{rng.randint(8, 40)}\\1c&H{rng.randint(0, 0xFFFFFF):06X}&}}{w[:3]}' for w in (rng.choice(WORDS) for _ in range(rng.randint(8, 18))))
        return f'Dialogue: 1,{start},{end},Default,,0,0,0,Karaoke,{{\\fad(150,150)\\blur2}}{syl}'
    if kind < 0.85:  # positioned sign with clip/transform
        return (f'Dialogue: 2,{start},{end},Sign,,0,0,0,,{{\\an7\\pos({rng.randint(0, 1900)},{rng.randint(0, 1060)})\\frz{rng.uniform(-30, 30):.2f}'
                f'\\clip({rng.randint(0, 900)},{rng.randint(0, 500)},{rng.randint(900, 1920)},{rng.randint(500, 1080)})\\t(0,500,\\fscx120\\fscy120)}}'
                f'{sentence(rng.randint(1, 4))}')
    return (f'Dialogue: 3,{start},{end},Sign,,0,0,0,,{{\\p1\\pos(960,540)}}m 0 0 l {rng.randint(10, 400)} 0 {rng.randint(10, 400)} '
            f'{rng.randint(10, 400)} 0 {rng.randint(10, 400)}{{\\p0}}')


def build(target_bytes, heavy):
    lines, size, t = [HEADER], len(HEADER.encode()), 1.0
    while True:
        line = dialogue(t, heavy) + '\n'
        b = len(line.encode('utf-8'))
        if size + b > target_bytes:
            break
        lines.append(line)
        size += b
        t += rng.uniform(0.05, 2.0) if heavy else rng.uniform(1.5, 4.0)
    return ''.join(lines)


typical = build(120 * 1024, False)
FIXTURES = {
    'typical': typical.encode('utf-8'),
    'typical-cp1250': typical.encode('cp1250', errors='replace'),
    'heavy': build(3 * 1024 * 1024, True).encode('utf-8'),
    'limit': build(LIMIT - 64, True).encode('utf-8'),
}


def load_converter():
    from app.modules.stream.router import _decode_subtitle_text
    from app.modules.stream.utils import subtitles
    if hasattr(subtitles, 'ass_to_vtt_cooperative'):
        async def step(raw):
            return await subtitles.ass_to_vtt_cooperative(await subtitles.decode_subtitle_text_cooperative(raw))
        return step, 'cooperative'
    async def step(raw):
        return subtitles.ass_to_vtt(_decode_subtitle_text(raw))
    return step, 'sync-inline'


async def measure(convert, raw, offload):
    gaps, stop = [], asyncio.Event()

    async def heartbeat():
        last = time.perf_counter()
        while not stop.is_set():
            await asyncio.sleep(0.001)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now
    hb = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.02)
    gaps.clear()
    t0, c0 = time.perf_counter(), time.thread_time()
    out = await convert(raw)
    cpu = (time.thread_time() - c0) * 1000
    wall = (time.perf_counter() - t0) * 1000
    await asyncio.sleep(0.01)
    stop.set()
    await hb
    return dict(wall_ms=wall, cpu_ms=cpu, max_loop_gap_ms=max(gaps) * 1000 if gaps else None, out=out)


def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


async def main():
    convert, err = load_converter()
    result = dict(label=sys.argv[1], smoke=SMOKE, python=sys.version, converter_available=convert is not None, converter_kind=err,
                  fixtures={k: dict(bytes=len(v), sha256=hashlib.sha256(v).hexdigest(), dialogue_lines=v.count(b'\nDialogue:')) for k, v in FIXTURES.items()},
                  cells=[])
    if convert is not None:
        warm, n = (1, 3) if SMOKE else (3, 20)
        for name, raw in FIXTURES.items():
            for offload in (False,):
                for _ in range(warm):
                    await measure(convert, raw, offload)
                runs = [await measure(convert, raw, offload) for _ in range(n)]
                outs = {hashlib.sha256(x['out'].encode()).hexdigest() for x in runs}
                first = runs[0]['out']
                wall = [x['wall_ms'] for x in runs]
                gap = [x['max_loop_gap_ms'] for x in runs]
                result['cells'].append(dict(fixture=name, mode=err, n=n, wall_ms=wall, max_loop_gap_ms=gap,
                                            cpu_ms=[x['cpu_ms'] for x in runs], wall_p50=pct(wall, .5), wall_p95=pct(wall, .95),
                                            gap_p50=pct(gap, .5), gap_p95=pct(gap, .95), output_sha256=sorted(outs), output_bytes=len(first.encode()),
                                            cues=first.count('-->'), starts_webvtt=first.startswith('WEBVTT')))
                print(name, err, f'wall p95 {pct(wall, .95):.2f} ms gap p95 {pct(gap, .95):.2f} ms', flush=True)
    json.dump(result, open(sys.argv[2], 'w'))

asyncio.run(main())
