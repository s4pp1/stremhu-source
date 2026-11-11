from pathlib import Path
import hashlib
import json

r=Path(__file__).parent
s=(r/'g01_matrix_native_v3.py').read_text()
s=s.replace("stream=await file.stream(f'g01-paced-play-{index}',f'g01-paced-user-{index}',0,total-1,ConnectedRequest(),raise_errors=True)", "stream=None if stream_count==0 else await file.stream(f'g01-paced-play-{index}',f'g01-paced-user-{index}',0,total-1,ConnectedRequest(),raise_errors=True)")
start=s.index('                for torrent,stream in readers:\n                    await stream.aclose()')
end=s.index('                assert not any(torrent.has_active_streams',start)
s=s[:start]+s[end:]
s=s.replace('g01-full-parameter-native-warm-seek-v3','g01-full-parameter-native-warm-seek-v4')
s=s.replace('# Existing stream generators are closed without starting them;\n            # remove their registrations by the real Stream.destroy contract.', '# No transient stream is created: destroying a registered stream\n            # can legitimately prefetch boundary pieces during its250ms grace.')
target=r/'g01_matrix_native_v4.py'
assert not target.exists()
target.write_text(s,encoding='utf-8')
s=(r/'run_g01_matrix_smoke_v3.py').read_text().replace('g01-matrix-edge-wiring-v3','g01-matrix-edge-wiring-v4').replace('g01_matrix_native_v3.py','g01_matrix_native_v4.py')
s=s.replace("if gate.exists() and not names:break", "if gate.exists() and (e/'cr17a-cold-GC-diagnostic-v4-after-4.json').exists() and not names:break")
s=s.replace("'Six separate actual native/Range edge wiring cases,NOT benchmark or whole432case matrix.", "'V3 idle wiring accidentally registered/destroyed a stream and observed legitimate boundary prefetch; failure retained. V4 never registers idle stream. Six separate actual native/Range edge wiring cases,NOT benchmark or whole432case matrix.")
controller=r/'run_g01_matrix_smoke_v4.py'
assert not controller.exists()
controller.write_text(s,encoding='utf-8')
print('V4 native idle setup corrected; V3 failed wiring retained, production untouched')
