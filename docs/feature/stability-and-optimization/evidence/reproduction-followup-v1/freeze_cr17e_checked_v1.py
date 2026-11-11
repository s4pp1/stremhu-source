"""Checked-source manifest for packet22b (cr17e-after-v1-source = git archive of the 22b server tree)."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
r = Path(__file__).parent; wt = Path(sys.argv[1]); commit = sys.argv[2]
src = r / 'cr17e-after-v1-source/server'
files = {p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.rglob('*')) if p.is_file()}
mismatch = [n for n, h in files.items() if hashlib.sha256((wt / 'server' / n).read_bytes()).hexdigest() != h]
assert not mismatch, mismatch[:5]
target = r / 'evidence/cr17e-checked-v1-manifest.json'
assert not target.exists()
target.write_text(json.dumps(dict(
    id='cr17e-checked-v1', checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), commit=commit,
    base_commit='41623ce (packet22 22731a4 cherry-picked onto packet21b d1da34c; server tree byte-identical to cr17d-after-v1-source)',
    frozen_source='cr17e-after-v1-source', worktree_identity_mismatches=0,
    checks=dict(
        targeted='test_search_resource_ownership: 7 passed (2 new: one shared read at a time; nested refusal and error-path release). Mutation check: with the limit disabled the concurrency test fails.',
        ruff_exit=0, basedpyright_exit=0, basedpyright_note='worktree has no .venv; run with --pythonpath of the repository venv (without it 565 unresolved-import errors)',
        pytest_exit=0, pytest_passed=611, snapshots=64, warnings=19,
        ownership_trace='g17 trace in Docker (C image, frozen 22b app): 4/4 cases, no overlapping Session calls, owner close before use none, pool 0, cleanup 0; two-alias-reads: reads serialized by the shared-read gate (alias_reads_met false; fixture barrier tolerates this). Packet22 source on the same trace: 4/4, alias_reads_met true.',
        pool_prescreen='cr17d-pool-diagnostic-v1 fixture, 2 runs each before/22b: peak checkouts 10-11 (before 10-11), physical connections 13-37 (before 33-60). Exploratory, not a gate.',
        note='Checks ran on the worktree whose server tree equals commit 5be09f2 (local); frozen copy is git archive of that tree, verified byte-identical.'),
    scope='Packet22b (CR17/d): packet22 plus database.shared_read_session(): a process-wide one-slot gate (non-reentrant, fail-fast) around the short isolated reads of shared searches (account refs, file snapshots). Writes (touch, create_many) unchanged.',
    files=files), indent=1), encoding='utf-8')
print('manifest', len(files))
