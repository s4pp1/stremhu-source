"""G17 API/ack probe against the pinned native binding, no network peers."""

import gc
import json
import tempfile
import threading
import time

import libtorrent as lt


with tempfile.TemporaryDirectory() as directory:
    native=lt.session({"listen_interfaces":"127.0.0.1:0","enable_dht":False,"enable_lsd":False,"enable_upnp":False,"enable_natpmp":False})
    methods={name:callable(getattr(native,name,None)) for name in ["abort","close","set_alert_notify","pause","get_torrents","pop_alerts"]}
    ready=threading.Event()
    native.set_alert_notify(ready.set)
    metadata={b"name":b"synthetic.mkv",b"piece length":16384,b"length":16384,b"pieces":b"\0"*20}
    info=lt.torrent_info(lt.bencode({b"info":metadata}))
    handle=native.add_torrent({"ti":info,"save_path":directory,"flags":lt.torrent_flags.paused})
    deadline=time.monotonic()+5
    # Drain unrelated startup alerts before the two requests being examined.
    native.pop_alerts()
    for _ in range(2):handle.save_resume_data(lt.save_resume_flags_t.flush_disk_cache)
    successes=failures=0
    while successes+failures<2 and time.monotonic()<deadline:
        ready.wait(.05);ready.clear()
        for alert in native.pop_alerts():
            if isinstance(alert,lt.save_resume_data_alert):successes+=1
            elif isinstance(alert,lt.save_resume_data_failed_alert):failures+=1
    native.set_alert_notify(lambda:None)
    native.pause()
    del handle,info,native
    gc.collect()
print(json.dumps(dict(fixture="g17-native-public-shutdown-api-v1",libtorrent=lt.__version__,methods=methods,two_save_requests_success=successes,two_save_requests_failure=failures,all_acknowledged=successes+failures==2,scope="Paused synthetic single native torrent, no peer/tracker, no payload restored; no unsupported close/abort call used.")))
