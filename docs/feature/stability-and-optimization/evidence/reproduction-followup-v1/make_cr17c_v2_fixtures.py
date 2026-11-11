"""Derive the cr17c-after-v2 fixtures from v1. Only the cold section changes:
a full gc.collect() right before each cold request (outside its timing) and
per-generation collection counts during the request. Everything else is byte-identical."""
from pathlib import Path
import re
import sys

r = Path(sys.argv[1])
CRLF, LF = chr(13) + chr(10), chr(10)
names = ['cr17c-policy-fixture', 'cr17c-policy-reference-fixture', 'cr17c-policy-direct-fixture', 'cr17c-kodi-ownership-observation']
old_head = """                for user_index in [0,1]:
                    cold_sql = statements
                    began = time.perf_counter()
"""
new_head = """                for user_index in [0,1]:
                    # v2: same GC phase for every cold request in every arm (cr17c-after-v1 heap/cold1 diagnostic).
                    gc.collect()
                    cold_gc = [stat['collections'] for stat in gc.get_stats()]
                    cold_sql = statements
                    began = time.perf_counter()
"""
pattern = re.compile(r"(                    cold\.append\(dict\(sql_statements=statements-cold_sql,count=count,user=user_index,wall_seconds=time\.perf_counter\(\)-began,result_count=total,payload_hash=digest)\)\)\n")
for name in names:
    raw = (r / f'{name}-v1.py').read_bytes().decode('utf-8')
    nl = CRLF if CRLF in raw else LF
    src = raw.replace(CRLF, LF)
    assert src.count(old_head) == 1, name
    src = src.replace(old_head, new_head)
    assert len(pattern.findall(src)) == 1, name
    src = pattern.sub(lambda m: m.group(1) + ",gc_collections=[stat['collections']-start for stat,start in zip(gc.get_stats(),cold_gc)]))\n", src)
    (r / f'{name}-v2.py').write_bytes(src.replace(LF, nl).encode('utf-8'))
    print(name, 'ok')
