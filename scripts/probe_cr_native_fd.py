"""Pinned native FD wakeup surface; no Python callback on libtorrent threads."""

import asyncio
import json
import socket

import libtorrent


async def main():
    reader, writer = socket.socketpair()
    reader.setblocking(False)
    writer.setblocking(False)
    holder = [libtorrent.session()]
    wake_bytes = 0
    statistics = 0
    try:
        native = holder[0]
        native.set_alert_fd(writer.fileno())
        native.pop_alerts()
        native.post_session_stats()
        deadline = asyncio.get_running_loop().time()+3
        while statistics == 0:
            async with asyncio.timeout_at(deadline):
                wake_bytes += len(await asyncio.get_running_loop().sock_recv(reader,4096))
            statistics += sum(isinstance(alert,libtorrent.session_stats_alert) for alert in native.pop_alerts())
        native.set_alert_fd(-1)
        native.pause()
        del native
        await asyncio.to_thread(holder.clear)
    finally:
        holder.clear()
        reader.close()
        writer.close()
    print(json.dumps(dict(fixture='native-fd-wakeup-surface-v1',native_version=libtorrent.version,wake_bytes=wake_bytes,statistics_alerts=statistics,negative_fd_setter_supported=True,native_reference_released=not holder,scope='Actual pinned binding and socketpair, networknone; one native stats wakeup and negative fd setter. Not a player/trust or full shutdown performance gate.')))


asyncio.run(main())
