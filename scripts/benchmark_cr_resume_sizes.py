"""Native resume-alert fixtures from disposable, already complete local data.

Run only in the network-disabled test container. Emits sizes and hashes, never
the resume bytes. Synthetic binary fixtures are written to /fixture-output.
"""

import hashlib
import json
import time
from pathlib import Path

import libtorrent


root = Path("/tmp/cr-resume-size-fixture")
root.mkdir()
output = Path("/fixture-output")
session = libtorrent.session()
session.apply_settings(dict(listen_interfaces="127.0.0.1:0", enable_dht=False, enable_lsd=False, enable_upnp=False, enable_natpmp=False))
rows = []
for count in (1, 24, 256):
    name = f"synthetic-pack-{count}"
    payload = b"x" * (count * 16)
    info = {b"name":name.encode(), b"piece length":16384, b"pieces":hashlib.sha1(payload).digest()}
    if count == 1:
        info[b"length"] = 16
        (root/name).write_bytes(b"x"*16)
    else:
        info[b"files"] = [{b"length":16, b"path":[f"episode-{index:04}.mkv".encode()]} for index in range(count)]
        (root/name).mkdir()
        for index in range(count):
            (root/name/f"episode-{index:04}.mkv").write_bytes(b"x"*16)
    params = libtorrent.add_torrent_params()
    params.ti = libtorrent.torrent_info(libtorrent.bencode({b"info":info}))
    params.save_path = str(root)
    params.flags |= libtorrent.torrent_flags.seed_mode
    params.flags &= ~libtorrent.torrent_flags.auto_managed
    params.flags |= libtorrent.torrent_flags.paused
    handle = session.add_torrent(params)
    handle.save_resume_data(libtorrent.save_resume_flags_t.flush_disk_cache)
    deadline, saved = time.monotonic()+15, None
    while time.monotonic() < deadline and saved is None:
        session.wait_for_alert(100)
        for alert in session.pop_alerts():
            if isinstance(alert, libtorrent.save_resume_data_alert):
                saved = libtorrent.bencode(libtorrent.write_resume_data(alert.params))
            elif isinstance(alert, libtorrent.save_resume_data_failed_alert):
                raise RuntimeError("Synthetic native resume generation failed")
    if saved is None:
        raise TimeoutError("Synthetic resume fixture readiness deadline exceeded")
    (output/f"resume-{count}.bin").write_bytes(saved)
    rows.append(dict(files=count, bytes=len(saved), sha256=hashlib.sha256(saved).hexdigest(), scaled_500_bytes=500*len(saved)))
    session.remove_torrent(handle)
print(json.dumps(dict(fixture="native-paused-seed-resume-flush-alert-v1", libtorrent_version=libtorrent.__version__, external_network=False, rows=rows)))
