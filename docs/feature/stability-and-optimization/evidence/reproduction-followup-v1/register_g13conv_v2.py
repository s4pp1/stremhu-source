"""Register the G13-convert v2 candidate gate before any measured run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
t = e / 'g13conv-v2-protocol.json'
if t.exists():
    raise SystemExit('Protocol already registered')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


after = json.loads((e / 'g13conv-v2-after-source-manifest.json').read_text(encoding='utf-8'))
p = dict(
    id='g13conv-v2', registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final candidate gate for the packet 31 OFFLOAD_CANDIDATE follow-up; registered before any measured run (only exploratory probes ran).',
    change=('Subtitle endpoint: decode_subtitle_text_cooperative (incremental UTF-8-sig / cp1250 fallback in 256 KiB slices) and ass_to_vtt_cooperative '
            '(~32 K-character slices cut right after a newline) with await asyncio.sleep(0) between slices; same output; no thread or process.'),
    before='frozen aaa9ee5 server/app (g02-post-cr17-v2 manifest; equals feature HEAD 8bffc56 server/app)',
    after=f"frozen {after['branch']} {after['commit']} server/app (g13conv-v2-after-source-manifest)",
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256=sha(r / 'g13conv-v2/bench.py'), controller_sha256=sha(r / 'g13conv_v2.py'), assessor_sha256=sha(r / 'assess_g13conv_v2.py'),
    fixtures='Same deterministic ASS fixtures and 1 ms heartbeat as g13conv-v1 (typical 120 KB UTF-8/cp1250, heavy ~3 MB, limit just under 8 MiB).',
    measured_step='The endpoint conversion step of the mounted source: before sync ass_to_vtt(_decode_subtitle_text(raw)); after the cooperative pair.',
    sampling='Two series x five before/after pairs, order alternating (ABBA); fresh 1-CPU process on cpuset 6 / 1 GiB / network none; 3 warmup + 20 conversions per fixture.',
    cpuset='6',
    exploration_before_registration=('Probe runs on the worktree: 1000-line slices left limit stall ~19 ms (decode 7.4 ms and splitlines 7.2 ms unsliced); slicing both '
                                     'gave ~8.7 ms at 1 MiB/128 K and ~2.5 ms median at 256 KiB/32 K; these sizes were then fixed. Probe data are not gate data.'),
    decision=('PASS iff correctness (20 runs, kinds, one output sha per fixture across before and after) and, per fixture, both series after medians of the per-run '
              'stall p95 < 10 ms, heavy/limit both below before min - J, and conversion wall p95 not repeatably above before max + J '
              '(J = max(|median before s1 - median before s2|, 0.01 ms)). INVALID on correctness, FAIL otherwise.'),
    limits='Microbenchmark of the endpoint step under a heartbeat loop; concurrent conversions interleave but are not separately measured. A/B lack the converter (N/A, see g13conv-v1).',
)
t.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding='utf-8')
print('registered', p['registered_at_utc'], sha(t)[:12])
