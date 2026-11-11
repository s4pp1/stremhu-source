"""Freeze the post-CR17 source manifest and register the G02 post-CR17 control protocol (v2) before any run."""
import datetime
import hashlib
import json
import pathlib

r = pathlib.Path(__file__).parent
e = r / 'evidence'
target = e / 'g02-post-cr17-v2-protocol.json'
if target.exists():
    raise SystemExit('Protocol already registered')
src = r / 'g02-post-cr17-v2-source/server/app'
files = {p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(src.rglob('*')) if p.is_file()}
(e / 'g02-post-cr17-v2-source-manifest.json').write_text(json.dumps(dict(commit='aaa9ee5', tree='e18855a123d6c39e589b28549f1f7a5a5b79b821', files=files), indent=1), encoding='utf-8')


def sha(name):
    return hashlib.sha256((r / name).read_bytes()).hexdigest()


protocol = dict(
    id='g02-post-cr17-control-v2',
    registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='Final G02 post-CR17 C control and decision rule; registered before any post-CR17 run',
    source='git archive of feature/stability-and-optimization aaa9ee5 server/app (tree e18855a1, equal to measured 22b); includes CR17 21b and 22+22b',
    source_scope_note=('Fixture uses app.common.database Base, torrent_files repository/models/schemas and indexer models. Versus the C baseline source only '
                       'additions differ (shared_read_session, TorrentFileSnapshot); engine/PRAGMA setup and touch/insert path unchanged. Static note, not a result.'),
    image='stremhu-source@sha256:bb87fa085976141178900796052b026577b3979ab7b9457c91693ef7acc4ae52',
    fixture_sha256=sha('g02-wal-fixture-v1.py'),
    controller_sha256=sha('g02_post_cr17_v2.py'),
    assessor_sha256=sha('assess_g02_post_cr17_v2.py'),
    summarizer_sha256=sha('g02_summarize_v2.py'),
    runs=['p1', 'p2'],
    cpuset='0,1',
    resources='Same as v1 C/A/B: 2 CPU affinity 0,1, 1 GiB, local Docker Desktop npipe, network none, read-only source, disposable task-labelled local volume per run.',
    references=dict(C_a='g02-before-a-v1.json', C_b='g02-before-b-v1.json', A='g02-full-reference-A-v1.json', B='g02-full-reference-B-v1.json'),
    correctness=('Per run: is_measurement, >=3600 s, 9 cells each >=400 s, zero errors, final pool checkouts 0, final checkpoint after all readers '
                 'closed busy=0 and log==checkpointed. Any failure => INVALID (stop, report; no decision).'),
    ordinary_path_rules=('Cells short/1,4,8 and select-await/1,4,8. WAL reuse: wal_header_epochs >= max(2, floor(min(C_a,C_b)/2)). Commit and transaction '
                         'p99 <= max(C_a,C_b)+|C_a-C_b| per cell. Ordinary-cell WAL high-water <= max ordinary high-water of C_a, C_b, A, B.'),
    decision=('NO_CHANGE if correctness holds and no ordinary rule fails in both runs for the same cell/metric: CR02 closes with measurement, '
              'no production PRAGMA/checkpoint change. PASSIVE_CANDIDATE if some ordinary rule fails in both runs (repeatable backlog/commit spike/'
              'storage): a separate CR02 candidate package is proposed; nothing is changed by this gate. Single-run failures are reported as noise.'),
    explicit_snapshot='explicit-snapshot cells are a stress control: WAL growth while a snapshot is held is reported, not judged; release is covered by the final-checkpoint correctness rule.',
    validation_before_registration='Assessor applied to existing references (C_a,C_b as posts) => NO_CHANGE; (A,B as posts) => NO_CHANGE with one single-run noise row.',
    limits='No storage SLO exists; the bound is the observed reference envelope. No speed claim. Diagnostic PASSIVE run is not a control.',
)
target.write_text(json.dumps(protocol, indent=1), encoding='utf-8')
print('registered', protocol['registered_at_utc'], hashlib.sha256(target.read_bytes()).hexdigest()[:12], 'files', len(files))
