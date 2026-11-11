"""Native resume sizes for sparse synthetic video-sized metadata.

No payload is downloaded or verified. A paused seed uses sparse disposable
files, then an alternate partial bitmap is encoded with the native codec.
The experiment measures resume bytes, not storage/seeding correctness.
Run in the network-disabled test container with a private fixture output.
"""

import gc
import hashlib
import json
import time
from pathlib import Path

import libtorrent

root = Path("/tmp/cr-resume-large-size-fixture")
root.mkdir()
output = Path("/fixture-output")
session = libtorrent.session()
session.apply_settings(dict(listen_interfaces="127.0.0.1:0", enable_dht=False, enable_lsd=False, enable_upnp=False, enable_natpmp=False))
rows = []
for size, piece_size in [(1 << 30, 256 << 10), (16 << 30, 1 << 20), (256 << 30, 1 << 20), (1 << 40, 1 << 20), (1 << 40, 256 << 10)]:
    name = f"synthetic-sparse-{size}-{piece_size}"
    count = (size + piece_size - 1) // piece_size
    with (root / name).open("wb") as file:
        file.truncate(size)
    info = {b"name":name.encode(), b"piece length":piece_size, b"length":size, b"pieces":hashlib.sha1(b"synthetic metadata only").digest() * count}
    params = libtorrent.add_torrent_params()
    try:
        params.ti = libtorrent.torrent_info(libtorrent.bencode({b"info":info}))
    except RuntimeError as error:
        rows.append(dict(logical_payload_bytes=size, piece_bytes=piece_size, piece_count=count, state="native-metadata-rejected", exception_kind=type(error).__name__))
        continue
    params.save_path = str(root)
    params.flags |= libtorrent.torrent_flags.seed_mode | libtorrent.torrent_flags.paused
    params.flags &= ~libtorrent.torrent_flags.auto_managed
    handle = session.add_torrent(params)
    handle.save_resume_data(libtorrent.save_resume_flags_t.flush_disk_cache)
    deadline, saved = time.monotonic() + 15, None
    while saved is None and time.monotonic() < deadline:
        session.wait_for_alert(100)
        for alert in session.pop_alerts():
            if isinstance(alert, libtorrent.save_resume_data_alert):
                saved = libtorrent.bencode(libtorrent.write_resume_data(alert.params))
            elif isinstance(alert, libtorrent.save_resume_data_failed_alert):
                raise RuntimeError("Synthetic sparse resume generation failed")
    if saved is None:
        raise TimeoutError("Synthetic sparse resume readiness deadline exceeded")
    partial = libtorrent.read_resume_data(saved)
    partial.have_pieces = [index % 2 == 0 for index in range(count)]
    partial.verified_pieces = []
    partial.flags &= ~libtorrent.torrent_flags.seed_mode
    partial_bytes = libtorrent.bencode(libtorrent.write_resume_data(partial))
    libtorrent.read_resume_data(partial_bytes)
    sizes = {}
    for state, data in [("seed-alert", saved), ("half-pieces-native-codec", partial_bytes)]:
        (output / f"large-resume-{state}-{size}-{piece_size}.bin").write_bytes(data)
        sizes[state] = len(data)
        rows.append(dict(logical_payload_bytes=size, piece_bytes=piece_size, piece_count=count, state=state, resume_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), scaled_500_bytes=500 * len(data)))
    rows.append(dict(logical_payload_bytes=size, piece_bytes=piece_size, workload="10 partial plus490 seed", resume_bytes=10 * sizes["half-pieces-native-codec"] + 490 * sizes["seed-alert"]))
    session.remove_torrent(handle)
    del params, partial, info, saved, partial_bytes, handle
    gc.collect()
print(json.dumps(dict(fixture="native-sparse-seed-alert-and-partial-codec-v1", libtorrent_version=libtorrent.__version__, external_network=False, verified_payload=False, rows=rows)))
