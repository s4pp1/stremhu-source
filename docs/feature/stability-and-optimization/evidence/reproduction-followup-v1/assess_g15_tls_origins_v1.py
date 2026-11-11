"""Summarize synthetic origin observations without copying certificates/keys."""
from pathlib import Path
import hashlib
import json

r = Path(__file__).parent
e = r / 'evidence'
cases = {}
raw = {}
for label in ['A', 'B', 'C']:
    name = f'g15-tls-origins-v1-{label}.json'
    data = json.loads((e / name).read_text())
    assert not data['is_measurement'] and len(data['rows']) == 18
    observed = {(row['mode'], row['target']): row for row in data['rows']}
    assert len(observed) == 18
    assert all(row['tls_hostname_verification'] for row in observed.values())
    assert len({row['sha256'] for row in observed.values()}) == 1
    assert all(row['decoded_bytes'] == 82073 for row in observed.values())
    cases[label] = observed
    raw[name] = hashlib.sha256((e / name).read_bytes()).hexdigest()
assert cases['A'] == cases['B'] == cases['C']
rows = list(cases['C'].values())
expected = {
    'fresh-host': [1, 1, 1, 0, 0, 0],
    'fresh-wide': [1, 1, 1, 1, 0, 0],
    'persisted': [1, 1, 1, 1, 1, 1],
}
targets = ['relative', 'same-origin', 'other-port', 'subdomain', 'other-host', 'downgrade']
for mode, counts in expected.items():
    assert [cases['C'][mode, target]['cookie_present_count'] for target in targets] == counts
report = dict(
    status='54 functional fixture observations complete; full G15 OPEN',
    targets=targets, cookie_present_by_mode=expected, observations=rows,
    interpretation=[
        'Cookie host/domain scope does not distinguish ports: fresh Secure host cookie reaches the other HTTPS port.',
        'Fresh Secure host/domain cookies are absent after the HTTP downgrade; persisted dict has lost that scope and reaches all tested destinations.',
        'The persisted-cookie path must be included in future per-hop origin enforcement; fresh-login-only testing is insufficient.',
    ],
    scope='Actual adapter constructor and IndexerClient, tiny native-valid body, verified ephemeral fixture TLS, no system/native trust changes. Only synthetic cookie presence counts. No production allowlist/default choice, no public SSRF or speed claim. Not G06.',
    raw_sha256=raw,
)
target = e / 'g15-tls-origins-assessment-v1.json'
assert not target.exists()
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(report['status'])
