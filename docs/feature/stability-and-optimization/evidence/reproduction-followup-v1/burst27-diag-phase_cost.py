"""Diagnostic only: cgroup anon cost per phase for 5 giant (21.5 MB, 10000-file) metadata bodies."""
import gc, json, sys
from pathlib import Path
sys.path.insert(0, '/fixture')
from metadata_sizes import make_metadata
from app.modules.torrent_files import models
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileSnapshot

def anon():
    stat = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    return int(stat['anon'])

def mib(v): return round(v / 2**20, 1)
gc.collect(); base = anon(); out = {}
template = make_metadata(1 << 40, 1 << 20, 10000)
bodies = [template.replace(b'synthetic-metadata-only', f'synthetic-metadata-{i:04d}'.encode()) for i in range(5)]
del template; gc.collect(); out['bytes_held'] = mib(anon() - base)
models_ = [TorrentFileModel(indexer_id='x', torrent_id=str(i), torrent_bytes=b) for i, b in enumerate(bodies)]
gc.collect(); out['models_created'] = mib(anon() - base)
snaps = [TorrentFileSnapshot.from_model(m) for m in models_]
gc.collect(); out['snapshots_built'] = mib(anon() - base)
del models_, bodies; gc.collect(); out['models_and_bytes_dropped'] = mib(anon() - base)
del snaps; gc.collect(); out['snapshots_dropped_cache_only'] = mib(anon() - base)
out['cache_entries'] = len(models._TORRENT_INFO_CACHE)
models._TORRENT_INFO_CACHE.clear(); gc.collect(); out['cache_cleared'] = mib(anon() - base)
print(json.dumps(dict(diagnostic='burst27-phase-cost-v1', is_measurement=False, giant_bytes=21491624, count=5, anon_delta_mib=out)))
