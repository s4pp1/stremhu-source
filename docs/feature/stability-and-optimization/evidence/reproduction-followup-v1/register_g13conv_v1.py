"""Register the G13-convert v1 protocol before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
t = e / 'g13conv-v1-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


p = dict(
    id='g13conv-v1', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final packet 31 (G13-convert) gate; registered before any measured run (only a 3-iteration C smoke ran).',
    question='After CR13/a,b, is synchronous ASS->VTT conversion on the event loop a remaining dominant loop-stall cost?',
    code_path=('stream/router.py subtitles endpoint: ass_to_vtt(_decode_subtitle_text(raw)) runs inline in the async handler; result cached per key; '
               'source capped by subtitle_max_source_bytes = 8 MiB.'),
    fixture_sha256=sha(r / 'g13conv-v1/bench.py'), controller_sha256=sha(r / 'g13conv_v1.py'), assessor_sha256=sha(r / 'assess_g13conv_v1.py'),
    images=dict(A='s4pp1/stremhu-source@sha256:a3a2012893d689795f958ccec666fef6277f8677f24efebe9568cb44ec7a0621',
                B='stremhu-source@sha256:6ca708d99b8698e6cf116a6183c283922ebd2e53940c366a93a421b4ca974a38',
                C='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52'),
    source_C='frozen aaa9ee5 server/app overlay (g02-post-cr17-v2 manifest re-verified); A/B use the image built-in app; missing converter => N/A.',
    fixtures=('Deterministic synthetic ASS: typical ~120 KB / 1202 dialogue lines (UTF-8 and cp1250 fallback), heavy ~3 MB karaoke/sign typesetting, '
              'limit just under 8 MiB. Synthetic, not a claim about every real file.'),
    sampling='5 repetitions x A/B/C rotated, each a fresh 1-CPU process on cpuset 6 / 1 GiB / network none; per fixture and mode 3 warmup + 20 timed conversions.',
    metric='Largest gap of a 1 ms asyncio heartbeat during one conversion (loop stall), per-run p95 over 20 conversions; wall and thread CPU time; output sha and cue count.',
    cpuset='6', repetitions=5,
    concurrency_note='Runs alongside G03 (CPU 2-5), G04 (12-14) and possibly the tail of G02 (0,1) on disjoint cpusets.',
    decision=('C inline: NO_CHANGE if every fixture median gap p95 < 10 ms (plan 10 ms piece/normal-HTTP budget); BUDGET_EXCEEDED_NOT_DOMINANT if >= 10 ms but none '
              '> 29.016 ms; OFFLOAD_CANDIDATE if some fixture median > 29.016 ms (largest remaining CR13/b post looplag p99-median, 500 fixture) with >= 2 runs above. '
              'INVALID on missing C runs, unavailable converter, non-WEBVTT or run-to-run output difference. to_thread results are informative design input only (GIL sharing).'),
    limits=('Microbenchmark of the exact production functions under a heartbeat loop, not a full-app looplag profile; the cache means one conversion per file key '
            'per process. No code change by this gate.'),
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
