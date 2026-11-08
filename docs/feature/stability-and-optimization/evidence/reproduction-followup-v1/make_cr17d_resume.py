"""Derive cr17d_after_v1_resume.py from the registered controller: identical run() and setup; the only changes are
(1) the controller-hash assert checks the registered controller file instead of itself and (2) the main loop runs
only the attempts not started before the 2026-11-07 power outage: long pair 2 (after, before)."""
from pathlib import Path
r = Path(__file__).parent
src = (r / 'cr17d_after_v1.py').read_bytes().decode('utf-8')
nl = '\r\n' if '\r\n' in src else '\n'
s = src.replace('\r\n', '\n')
old_assert = "assert protocol['controller_sha256'] == sha(Path(__file__))\n"
assert s.count(old_assert) == 1
s = s.replace(old_assert, "assert protocol['controller_sha256'] == sha(r / 'cr17d_after_v1.py')\n")
cut = s.index("for label in ['after', 'before']:\n    run('smoke'")
tail = '''# Resume after the power outage: the interrupted attempt long-after-pair-2 produced no output and is recorded
# as interrupted; the remaining configured attempts run unchanged. Earlier failures are collected from disk.
failed = sorted(p.name[:-len('-failed.json')] for p in e.glob('cr17d-after-v1-*-failed.json'))
for label in ['after', 'before']:
    print(f'long {label} pair 2 starting full1800seconds (resume)', flush=True)
    run('long', label, 'pair', 2, POLICY, '--heap-profile', cpus='6,7', timeout=3600)
(e / 'cr17d-after-v1-complete.json').write_text(json.dumps(dict(
    protocol=protocol['id'], status='All configured attempts finished; NOT acceptance', failed_attempts=failed,
    interrupted_attempts=['cr17d-after-v1-long-after-pair-2 (power outage 2026-11-07; no output; rerun once by resume amendment)'],
    amendment='cr17d-after-v1-resume-amendment.json')), encoding='utf-8')
print('All cr17d-after-v1 attempts finished; failed:', failed, flush=True)
sys.exit(0)
'''
s = s[:cut] + tail
(r / 'cr17d_after_v1_resume.py').write_bytes(s.replace('\n', nl).encode('utf-8'))
print('ok')
