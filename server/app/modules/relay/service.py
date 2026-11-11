import asyncio
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass

import libtorrent as libtorrent
from fastapi import HTTPException

from app.common.async_utils import owned_to_thread
from app.common.logger import logger
from app.common.singleflight import SearchStoppingError
from app.common.torrent_info import parse_torrent_info
from app.config import config
from app.modules.relay.entities import File, Stream, Torrent
from app.modules.relay.schemas import (
    RelaySettingsUpdate,
    RelayTorrent,
)
from app.modules.settings.enums import RelayEncryptionEnum


def encryption_settings(mode: RelayEncryptionEnum) -> "libtorrent.settings_pack":
    """A BitTorrent protokoll-titkosítás (MSE/PE) libtorrent beállításai.

    - enabled: a titkosított és a titkosítatlan kapcsolat is engedélyezett (libtorrent alapértelmezés)
    - forced: csak titkosított kapcsolat jöhet létre, a kézfogás után is RC4 titkosítással
    - disabled: a titkosítás ki van kapcsolva
    """
    if mode == RelayEncryptionEnum.FORCED:
        return {
            "out_enc_policy": libtorrent.enc_policy.forced,
            "in_enc_policy": libtorrent.enc_policy.forced,
            "allowed_enc_level": libtorrent.enc_level.rc4,
            "prefer_rc4": True,
        }

    if mode == RelayEncryptionEnum.DISABLED:
        return {
            "out_enc_policy": libtorrent.enc_policy.disabled,
            "in_enc_policy": libtorrent.enc_policy.disabled,
            "allowed_enc_level": libtorrent.enc_level.both,
            "prefer_rc4": False,
        }

    return {
        "out_enc_policy": libtorrent.enc_policy.enabled,
        "in_enc_policy": libtorrent.enc_policy.enabled,
        "allowed_enc_level": libtorrent.enc_level.both,
        "prefer_rc4": False,
    }


class PieceReadAbortedError(Exception):
    """A darabolvasás a torrent eltávolítása vagy leállítás miatt megszakadt."""


@dataclass(frozen=True)
class ResumeSaveResult:
    requested: int
    accepted: int
    failed: int
    timed_out: int

    @property
    def complete(self) -> bool:
        return self.failed == self.timed_out == 0


class RelayService:
    def __init__(
        self,
    ):
        self._accepting = True
        self._closed = False
        self._native_close_task: asyncio.Task[None] | None = None
        self._alert_task: asyncio.Task[None] | None = None
        self._alert_failed = False
        self._resume_pending: dict[str, asyncio.Future[bool]] = {}
        self._libtorrent_session = libtorrent.session()

        alert_mask = (
            libtorrent.alert_category.error
            | libtorrent.alert_category.storage
            | libtorrent.alert_category.status
            | libtorrent.alert_category.piece_progress
        )

        self._libtorrent_session.apply_settings(
            {
                "alert_mask": alert_mask,
                "listen_interfaces": f"0.0.0.0:{config.libtorrent_port},[::]:{config.libtorrent_port}",
                "connections_limit": 300,
                "enable_dht": False,
                "enable_lsd": False,
                "auto_sequential": False,
                "piece_extent_affinity": True,
                "peer_timeout": 60,
                "piece_timeout": 10,
                "request_timeout": 30,
                "unchoke_interval": 10,
                "active_downloads": -1,
                "active_seeds": -1,
                "active_limit": -1,
                "connection_speed": 100,
                "mixed_mode_algorithm": libtorrent.bandwidth_mixed_algo_t.prefer_tcp,
                "unchoke_slots_limit": 16,
                "min_reconnect_time": 5,
                "strict_end_game_mode": False,
                "optimistic_unchoke_interval": 20,
            }
        )

        self._connection_policy_lock = threading.RLock()
        self._torrent_connections_limit = 20
        self._torrents: dict[libtorrent.sha1_hash, Torrent] = {}
        self._loop = asyncio.get_event_loop()
        self.priority_update_queue: asyncio.Queue[str] = asyncio.Queue()

        self._piece_fetch_tasks: dict[tuple[str, int], asyncio.Task[bytes]] = {}
        self._pending_piece_reads: dict[tuple[str, int], asyncio.Future[bytes]] = {}

        # Event hooks for resume data management (Observer Pattern)
        self.on_save_resume: list[Callable[[str, bytes], bool | None]] = []

        # The binding's Python callback requires the GIL on a native thread.
        # Its documented Python interface is an FD wakeup instead. Both ends
        # stay open until the native owner is really gone, preventing fd reuse.
        self._alert_reader, self._alert_writer = socket.socketpair()
        self._alert_reader.setblocking(False)
        self._alert_writer.setblocking(False)
        self._libtorrent_session.set_alert_fd(self._alert_writer.fileno())
        self._alert_task = self._loop.create_task(self._pump_alerts(), name="relay-alerts")
        self._alert_task.add_done_callback(self._alert_task_finished)

    async def _pump_alerts(self) -> None:
        # Startup alerts may already have been queued before fd registration.
        self.process_alerts()
        while not self._closed:
            data = await self._loop.sock_recv(self._alert_reader, 4096)
            if not data:
                raise RuntimeError("Native alert channel closed")
            self.process_alerts()

    def _alert_task_finished(self, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is None:
            return
        self._alert_failed = True
        self.stop_admission()
        logger.error("Native alert channel failed: kind=%s", type(error).__name__)
        for key in tuple(self._resume_pending):
            self._finish_resume(key, False)
        for future in self._pending_piece_reads.values():
            if not future.done():
                future.set_exception(PieceReadAbortedError("Native alert channel stopped"))

    def trigger_priority_update(
        self,
        info_hash: str,
    ) -> None:
        if not getattr(self, "_accepting", True):
            return
        self._loop.call_soon_threadsafe(
            self._enqueue_priority, info_hash
        )

    def _enqueue_priority(self, info_hash: str) -> None:
        if getattr(self, "_accepting", True):
            self.priority_update_queue.put_nowait(info_hash)

    def stop_admission(self) -> None:
        self._accepting = False

    async def priority_manager_loop(self):
        while True:
            # Várjuk meg az első beérkező kérést
            info_hash = await self.priority_update_queue.get()
            info_hashes = {info_hash}

            # Szedjük ki az összes többit is, ami esetleg várakozik (a set deduplikál)
            while not self.priority_update_queue.empty():
                try:
                    info_hashes.add(self.priority_update_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            for info_hash in info_hashes:
                sha1_hash = self._parse_info_hash(info_hash)
                if torrent := self._torrents.get(sha1_hash):
                    await owned_to_thread(torrent.priority_manager)

    def update_settings(
        self,
        payload: RelaySettingsUpdate,
    ):
        apply_settings: libtorrent.settings_pack = {}

        if payload.download_limit is not None:
            apply_settings["download_rate_limit"] = payload.download_limit

        if payload.upload_limit is not None:
            apply_settings["upload_rate_limit"] = payload.upload_limit

        if payload.connections_limit is not None:
            apply_settings["connections_limit"] = payload.connections_limit

        if payload.enable_upnp_and_natpmp is not None:
            apply_settings["enable_upnp"] = payload.enable_upnp_and_natpmp
            apply_settings["enable_natpmp"] = payload.enable_upnp_and_natpmp

        if payload.torrent_connections_limit is not None:
            with self._connection_policy_lock:
                self._torrent_connections_limit = payload.torrent_connections_limit
                for torrent in list(self._torrents.values()):
                    self.apply_torrent_connection_policy(torrent)

        if payload.encryption is not None:
            apply_settings.update(encryption_settings(payload.encryption))

        if payload.enable_utp is not None:
            apply_settings["enable_outgoing_utp"] = payload.enable_utp
            apply_settings["enable_incoming_utp"] = payload.enable_utp

        if payload.port is not None:
            apply_settings["listen_interfaces"] = (
                f"0.0.0.0:{payload.port},[::]:{payload.port}"
            )

        self._libtorrent_session.apply_settings(apply_settings)

    def apply_torrent_connection_policy(self, torrent: Torrent) -> None:
        with self._connection_policy_lock:
            handle = torrent.torrent_handle
            try:
                owned = self._torrents.get(self._parse_info_hash(torrent.info_hash)) is torrent
                if not owned or not handle.is_valid():
                    torrent._last_applied_limit = None
                    torrent._last_applied_handle = None
                    return
                target = max(self._torrent_connections_limit, 50) if torrent.has_active_streams else self._torrent_connections_limit
                if torrent._last_applied_limit == target and torrent._last_applied_handle is handle:
                    return
                # A failed native call leaves the actual value unknown. A later
                # call must retry even if the policy returns to the old target.
                torrent._last_applied_limit = None
                torrent._last_applied_handle = None
                handle.set_max_connections(target)
            except Exception:
                torrent._last_applied_limit = None
                torrent._last_applied_handle = None
                raise
            torrent._last_applied_limit = target
            torrent._last_applied_handle = handle

    def get_torrents(self) -> list[RelayTorrent]:
        torrent_handlers = self._get_torrents()

        return [
            RelayTorrent.from_libtorrent_handle(torrent_handle)
            for torrent_handle in torrent_handlers
        ]

    def get_active_streams(self) -> list[Stream]:
        streams = []
        for torrent in list(self._torrents.values()):
            for file in list(torrent.files.values()):
                streams.extend(list(file.streams.values()))
        return streams

    def get_torrent_file(self, info_hash: str, file_index: int) -> File:
        sha1_info_hash = self._parse_info_hash(info_hash)

        torrent = self._torrents.get(sha1_info_hash)
        if torrent is None:
            raise HTTPException(404, f'"{info_hash}" torrent nem található.')

        file = torrent.files.get(file_index)
        if file is None:
            raise HTTPException(400, "Érvénytelen fájl index.")

        return file

    async def get_piece_data(
        self,
        torrent_handle: libtorrent.torrent_handle,
        piece_index: int,
    ) -> bytes:
        if not getattr(self, "_accepting", True):
            raise PieceReadAbortedError("Relay is stopping")
        info_hash = str(torrent_handle.info_hash())
        request_key = (info_hash, piece_index)

        task = self._piece_fetch_tasks.get(request_key)
        if task is None or task.done():
            task = asyncio.create_task(
                self._fetch_piece_with_retry(torrent_handle, piece_index, request_key)
            )
            self._piece_fetch_tasks[request_key] = task
            task.add_done_callback(self._consume_piece_exception)

        return await asyncio.shield(task)

    @staticmethod
    def _consume_piece_exception(task: asyncio.Task[bytes]) -> None:
        # Minden HTTP-várakozó lecsatlakozhatott, mielőtt a közös task befejeződik;
        # a kivételt lekérjük, hogy ne keletkezzen "Task exception was never retrieved".
        if not task.cancelled():
            task.exception()

    def cancel_piece_requests(self, info_hash: str) -> None:
        """Az adott torrent összes függő darabolvasását lezárja.

        Az event loopon kell futnia (worker szálról `call_soon_threadsafe`-fel ütemezve).
        A függő olvasások felismerhető `PieceReadAbortedError`-t kapnak; a jelenleg
        újrapróbálkozási szünetben lévő (future nélküli) taskokat töröljük.
        """
        aborted_keys: set[tuple[str, int]] = set()
        for key, future in list(self._pending_piece_reads.items()):
            if key[0] == info_hash:
                self._pending_piece_reads.pop(key, None)
                aborted_keys.add(key)
                if not future.done():
                    future.set_exception(
                        PieceReadAbortedError(f"A torrent ({info_hash}) eltávolításra került.")
                    )

        for key, task in list(self._piece_fetch_tasks.items()):
            if key[0] == info_hash and key not in aborted_keys:
                if not task.done():
                    task.cancel()

    async def close_piece_requests(self) -> None:
        """Leállításkor az összes darabolvasó task leállítása és megvárása."""
        self.stop_admission()
        tasks = list(self._piece_fetch_tasks.values())
        for task in tasks:
            task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException) and not isinstance(
                result, (asyncio.CancelledError, PieceReadAbortedError, TimeoutError)
            ):
                logger.debug("Piece cleanup failed: kind=%s", type(result).__name__)

    async def _fetch_piece_with_retry(
        self,
        torrent_handle: libtorrent.torrent_handle,
        piece_index: int,
        request_key: tuple[str, int],
    ) -> bytes:
        try:
            # A teljes újrapróbálkozási sorozatnak is van felső határa.
            async with asyncio.timeout(config.relay_piece_timeout_seconds):
                for attempt in range(4):
                    try:
                        return await self._fetch_piece_once(
                            torrent_handle, piece_index, request_key
                        )
                    except FileNotFoundError:
                        if attempt < 3:
                            await asyncio.sleep(0.5)
                            continue
                        raise
            raise RuntimeError("Unreachable")
        finally:
            if self._piece_fetch_tasks.get(request_key) is asyncio.current_task():
                self._piece_fetch_tasks.pop(request_key, None)

    async def _fetch_piece_once(
        self,
        torrent_handle: libtorrent.torrent_handle,
        piece_index: int,
        request_key: tuple[str, int],
    ) -> bytes:
        future: asyncio.Future[bytes] = self._loop.create_future()
        self._pending_piece_reads[request_key] = future

        try:
            if torrent_handle.have_piece(piece_index):
                torrent_handle.read_piece(piece_index)
                return await asyncio.wait_for(
                    future, timeout=config.relay_read_timeout_seconds
                )
            return await future
        finally:
            if self._pending_piece_reads.get(request_key) is future:
                self._pending_piece_reads.pop(request_key, None)
            if not future.done():
                future.cancel()

    def add_torrent(
        self,
        torrent_bytes: bytes,
        priority: int = 0,
        resume_bytes: bytes | None = None,
    ) -> RelayTorrent:
        if not getattr(self, "_accepting", True):
            raise SearchStoppingError("Relay is stopping")
        save_path = str(config.downloads_dir.absolute())

        try:
            torrent_info = libtorrent.torrent_info(torrent_bytes)
        except Exception:
            raise HTTPException(400, "A torrent nem érvényes.")

        params: libtorrent.add_torrent_params | None = None
        if resume_bytes:
            params = libtorrent.read_resume_data(resume_bytes)

        if params is None:
            params = libtorrent.add_torrent_params()

        params.ti = torrent_info
        params.save_path = save_path
        params.storage_mode = libtorrent.storage_mode_t.storage_mode_sparse

        torrent_handle = self._libtorrent_session.add_torrent(params)
        torrent_handle.unset_flags(libtorrent.torrent_flags.disable_pex)

        priorities = torrent_handle.piece_priorities()
        torrent_handle.prioritize_pieces([priority] * len(priorities))

        parsed_torrent_info = parse_torrent_info(torrent_info)

        torrent = Torrent(
            torrent_handle=torrent_handle,
            torrent_info=parsed_torrent_info,
            service=self,
            default_priority=priority,
        )

        with self._connection_policy_lock:
            self._torrents[torrent_info.info_hash()] = torrent
            self.apply_torrent_connection_policy(torrent)

        return RelayTorrent.from_libtorrent_handle(torrent_handle)

    def get_torrent(
        self,
        info_hash: str,
    ) -> RelayTorrent | None:
        sha1_info_hash = self._parse_info_hash(info_hash)
        torrent_handle = self._get_torrent(sha1_info_hash)

        if torrent_handle is None:
            return None

        return RelayTorrent.from_libtorrent_handle(torrent_handle)

    def is_file_downloaded(
        self,
        info_hash: str,
        file_index: int,
        file_size: int,
    ) -> bool:
        sha1_info_hash = self._parse_info_hash(info_hash)
        torrent = self._torrents.get(sha1_info_hash)
        if torrent is None or not torrent.torrent_handle.is_valid():
            return False

        status = torrent.torrent_handle.status()
        if status.is_seeding:
            return True

        try:
            progress = torrent.torrent_handle.file_progress()
            if 0 <= file_index < len(progress):
                return file_size > 0 and progress[file_index] >= file_size
        except Exception:
            return False

        return False

    def get_torrent_or_raise(
        self,
        info_hash: str,
    ) -> RelayTorrent:
        relay_torrent = self.get_torrent(
            info_hash=info_hash,
        )

        if relay_torrent is None:
            raise HTTPException(404, f'"{info_hash}" torrent nem található.')

        return relay_torrent

    def delete_torrent(
        self,
        info_hash: str,
    ) -> bool:
        sha1_info_hash = self._parse_info_hash(info_hash)

        return self._delete_torrent(sha1_info_hash)

    def _delete_torrent(self, info_hash: libtorrent.sha1_hash) -> bool:
        torrent_handle = self._get_torrent(info_hash)

        if torrent_handle is None:
            return False

        with self._connection_policy_lock:
            self._torrents.pop(info_hash, None)
        self._loop.call_soon_threadsafe(self.cancel_piece_requests, str(info_hash))

        self._libtorrent_session.remove_torrent(
            torrent_handle,
            libtorrent.options_t.delete_files,
        )

        return True

    def _request_resume(self, handle: libtorrent.torrent_handle) -> asyncio.Future[bool]:
        key = str(handle.info_hash())
        previous = self._resume_pending.get(key)
        if previous is not None:
            return previous
        result: asyncio.Future[bool] = self._loop.create_future()
        # Install before the native call: even an immediate alert has an owner.
        self._resume_pending[key] = result
        try:
            handle.save_resume_data(libtorrent.save_resume_flags_t.flush_disk_cache)
        except Exception as error:
            self._finish_resume(key, False)
            logger.error("Resume request failed: kind=%s", type(error).__name__)
        return result

    def _finish_resume(self, key: str, accepted: bool) -> None:
        future = getattr(self, "_resume_pending", {}).pop(key, None)
        if future is not None and not future.done():
            future.set_result(accepted)

    def trigger_save_resume_data(self) -> None:
        if not self._accepting:
            return
        for handle in self._get_torrents():
            self._request_resume(handle)

    async def save_final_resume(self, timeout: float = 5.0) -> ResumeSaveResult:
        """Old periodic alerts must finish before a final request for that hash.

        A timeout leaves the old request in place; a late old alert can never
        acknowledge a new final request. The writer and native pump stay alive.
        """
        if getattr(self, "_alert_failed", False) or getattr(self, "_closed", False):
            return ResumeSaveResult(0, 0, 1, 0)
        deadline = self._loop.time() + timeout
        previous = tuple(self._resume_pending.values())
        if previous:
            _, pending = await asyncio.wait(previous, timeout=max(0, deadline-self._loop.time()))
            if pending:
                return ResumeSaveResult(0, 0, 0, len(pending))
        handles = self._get_torrents()
        requests = [self._request_resume(handle) for handle in handles]
        if not requests:
            return ResumeSaveResult(0, 0, 0, 0)
        done, pending = await asyncio.wait(requests, timeout=max(0, deadline-self._loop.time()))
        accepted = sum(future.result() for future in done)
        return ResumeSaveResult(len(requests), accepted, len(done)-accepted, len(pending))

    async def close_native(self) -> None:
        from app.common.async_utils import await_owned_task

        if self._native_close_task is None:
            self._native_close_task = asyncio.create_task(self._release_native(), name="relay-native-close")
        await await_owned_task(self._native_close_task)

    async def _release_native(self) -> None:
        self.stop_admission()
        self._closed = True
        alert_task = getattr(self, "_alert_task", None)
        if alert_task is not None:
            if not alert_task.done():
                alert_task.cancel()
            await asyncio.gather(alert_task, return_exceptions=True)
        try:
            # This keeps a native-only notification function, with no Python
            # callback/GIL dependency. The sockets remain owned until join.
            self._libtorrent_session.set_alert_fd(-1)
            self._libtorrent_session.pause()
        finally:
            for future in self._resume_pending.values():
                if not future.done():
                    future.set_result(False)
            self._resume_pending.clear()
            self.on_save_resume.clear()
            # Drop all owned handle references before releasing the native
            # session's last reference on a worker (2.1.1 has no abort/close).
            self._torrents.clear()
            while not self.priority_update_queue.empty():
                self.priority_update_queue.get_nowait()
            holder = [self._libtorrent_session]
            del self._libtorrent_session
            try:
                await owned_to_thread(holder.clear)
            finally:
                reader = getattr(self, "_alert_reader", None)
                writer = getattr(self, "_alert_writer", None)
                if reader is not None:
                    reader.close()
                if writer is not None:
                    writer.close()
        if getattr(self, "_alert_failed", False):
            raise RuntimeError("Native alert channel failed")

    def process_alerts(self):
        if getattr(self, "_closed", False):
            return
        alerts = self._libtorrent_session.pop_alerts()

        for alert in alerts:
            try:
                match alert:
                    case libtorrent.save_resume_data_alert():
                        key = str(alert.handle.info_hash())
                        accepted = True
                        try:
                            resume_data = libtorrent.bencode(
                                libtorrent.write_resume_data(alert.params)
                            )
                            torrent_handle = alert.handle
                            if torrent_handle.is_valid():
                                info_hash_str = str(torrent_handle.info_hash())

                                for callback in tuple(self.on_save_resume):
                                    try:
                                        if callback(info_hash_str, resume_data) is False:
                                            accepted = False
                                    except Exception as error:
                                        accepted = False
                                        logger.error(
                                            "Resume callback failed: kind=%s", type(error).__name__
                                        )
                            else:
                                accepted = False
                        except Exception as error:
                            accepted = False
                            logger.error(
                                "Resume serialization failed: kind=%s", type(error).__name__
                            )
                        finally:
                            self._finish_resume(key, accepted)

                    case libtorrent.save_resume_data_failed_alert():
                        self._finish_resume(str(alert.handle.info_hash()), False)
                        logger.error(
                            "Resume snapshot alert failed: kind=%s", type(alert).__name__
                        )

                    case libtorrent.piece_finished_alert():
                        info_hash = str(alert.handle.info_hash())
                        piece_index = alert.piece_index
                        request_key = (info_hash, piece_index)
                        if request_key in self._pending_piece_reads:
                            alert.handle.read_piece(piece_index)
                        self.trigger_priority_update(info_hash)

                    case libtorrent.read_piece_alert():
                        info_hash = str(alert.handle.info_hash())
                        request_key = (info_hash, alert.piece)

                        if future := self._pending_piece_reads.pop(request_key, None):
                            has_error = alert.error and alert.error.value() != 0

                            if has_error:
                                error_msg = alert.error.message()
                                error_code = alert.error.value()

                                logger.error(
                                    "Native piece read failed: code=%s", error_code
                                )

                                if error_code in (2, 3):
                                    err = FileNotFoundError(error_msg)
                                else:
                                    err = Exception(error_msg)

                                if not future.done():
                                    future.set_exception(err)
                            else:
                                piece_data = bytes(alert.buffer)
                                if not future.done():
                                    future.set_result(piece_data)

            except Exception as error:
                logger.error("Native alert failed: alert=%s kind=%s", type(alert).__name__, type(error).__name__)

    def _parse_info_hash(
        self,
        info_hash_str: str,
    ) -> libtorrent.sha1_hash:
        info_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return info_hash

    def _get_torrents(
        self,
    ) -> list[libtorrent.torrent_handle]:
        torrent_handlers = self._libtorrent_session.get_torrents()

        valid_torrent_handlers = [
            torrent_handler
            for torrent_handler in torrent_handlers
            if torrent_handler.is_valid()
        ]

        return valid_torrent_handlers

    def _get_torrent(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> libtorrent.torrent_handle | None:
        torrent_handle = self._libtorrent_session.find_torrent(info_hash)

        if not torrent_handle.is_valid():
            return None

        return torrent_handle
