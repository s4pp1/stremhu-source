"""Same core HTTP workload, extended with actual cgroup/proc memory counters.

The original fixture remains unchanged for its historical packet evidence.
This wrapper changes only the final report, before any CR17 core series runs.
"""

import json
import runpy
from pathlib import Path


def report(serialized: str, **kwargs) -> None:
    data = json.loads(serialized)
    if data['fixture'] != 'core-http-v1-empty-streams':
        raise RuntimeError('Unexpected core fixture report')
    stat = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    data['container_memory'] = {
        'current_bytes': int(Path('/sys/fs/cgroup/memory.current').read_text()),
        'peak_bytes': int(Path('/sys/fs/cgroup/memory.peak').read_text()),
        'anon_bytes': int(stat['anon']),
        'file_bytes': int(stat['file']),
    }
    status = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        name, _, value = line.partition(':')
        if name in {'VmRSS', 'VmHWM', 'RssAnon', 'RssFile'}:
            status[name+'_kib'] = int(value.split()[0])
        elif name == 'Threads':
            status['threads'] = int(value.strip())
    data['process_memory'] = status
    data['resource_probe'] = 'cgroup2 anon/file/current/peak and current process RSS/HWM/OS threads v2'
    print(json.dumps(data), **kwargs)


runpy.run_path(
    str(Path(__file__).with_name('benchmark_cr_core.py')),
    init_globals={'print': report},
    run_name='__main__',
)
