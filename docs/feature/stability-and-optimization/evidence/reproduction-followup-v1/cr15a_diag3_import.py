import sys, gc, time
from pathlib import Path
def rss_anon():
    for l in Path('/proc/self/status').read_text().splitlines():
        if l.startswith('RssAnon:'): return int(l.split()[1])*1024
def anon():
    time.sleep(3)
    stat=dict(l.split() for l in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()); return int(stat['anon'])
import httpx, libtorrent
from app.modules.indexer_definitions.base_indexer_definition import IndexerClient
from app.modules.indexer_definitions.integrations.ncore import NcoreIndexerDefinition
gc.collect(); a0=anon(); r0=rss_anon()
print('config_loaded_after_probe_imports', 'app.config' in sys.modules)
mods0=set(sys.modules)
import app.config
gc.collect(); a1=anon(); r1=rss_anon()
print('new_modules', len(set(sys.modules)-mods0), 'cgroup_anon_delta_mib', round((a1-a0)/1048576,2), 'rss_anon_delta_mib', round((r1-r0)/1048576,2), 'cgroup_anon_mib', round(a1/1048576,1))
