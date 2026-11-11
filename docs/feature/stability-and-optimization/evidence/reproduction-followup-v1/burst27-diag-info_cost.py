"""Diagnostic only: retained Python heap of one parsed TorrentInfo per metadata profile (tracemalloc)."""
import gc, json, sys, tracemalloc
sys.path.insert(0, '/fixture')
from metadata_sizes import make_metadata
from app.modules.torrent_files import models
from app.modules.torrent_files.models import TorrentFileModel
PROFILES = {"movie": (10 << 30, 4 << 20, 1), "pack": (40 << 30, 8 << 20, 24), "remux": (80 << 30, 4 << 20, 1),
            "season-box": (256 << 30, 4 << 20, 1000), "giant-valid": (1 << 40, 1 << 20, 10000)}
rows = []
for name, (total, piece, files) in PROFILES.items():
    body = make_metadata(total, piece, files)
    models._TORRENT_INFO_CACHE.clear(); gc.collect()
    tracemalloc.start()
    model = TorrentFileModel(indexer_id='x', torrent_id=name, torrent_bytes=body)
    info = model.info
    gc.collect()
    held_with_model, peak = tracemalloc.get_traced_memory()
    del model; gc.collect()
    held_cache_only, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rows.append(dict(profile=name, metadata_bytes=len(body), files=files, cache_entries=len(models._TORRENT_INFO_CACHE),
                     traced_with_model=held_with_model, traced_cache_and_info=held_cache_only, traced_peak=peak))
    del info, body; models._TORRENT_INFO_CACHE.clear(); gc.collect()
print(json.dumps(dict(diagnostic='burst27-info-cost-v1', is_measurement=False, rows=rows, cache_max=models._MAX_TORRENT_INFO_CACHE)))
