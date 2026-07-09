import asyncio
from collections.abc import Callable
from typing import Any

import libtorrent as libtorrent
from fastapi import HTTPException

from app.common.logger import logger
from app.common.torrent_info import parse_torrent_info
from app.config import config
from app.modules.relay.entities import File, Stream, Torrent
from app.modules.relay.schemas import (
    RelaySettingsUpdate,
    RelayTorrent,
)


class RelayService:
    def __init__(
        self,
    ):
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
                "peer_timeout": 10,
                "piece_extent_affinity": True,
                "piece_timeout": 5,
                "request_timeout": 5,
                "unchoke_interval": 1,
                "active_downloads": -1,
                "active_seeds": -1,
                "active_limit": -1,
                "connection_speed": 100,
                "mixed_mode_algorithm": libtorrent.bandwidth_mixed_algo_t.prefer_tcp,
                "unchoke_slots_limit": 16,
            }
        )

        self._torrent_connections_limit = 20
        self._torrents: dict[libtorrent.sha1_hash, Torrent] = {}
        self.loop = asyncio.get_event_loop()
        self.priority_update_queue: asyncio.Queue[str] = asyncio.Queue()

        def on_alert():
            self.loop.call_soon_threadsafe(self.process_alerts)

        self._libtorrent_session.set_alert_notify(on_alert)

        self.pending_piece_requests: dict[
            tuple[str, int], list[asyncio.Future[bytes]]
        ] = {}

        # Event hooks for resume data management (Observer Pattern)
        self.on_save_resume: list[Callable[[str, bytes], None]] = []

    def trigger_priority_update(
        self,
        info_hash: str,
    ) -> None:
        self.loop.call_soon_threadsafe(self.priority_update_queue.put_nowait, info_hash)

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
                    await asyncio.to_thread(torrent.priority_manager)

    def update_settings(
        self,
        payload: RelaySettingsUpdate,
    ):
        apply_settings: dict[str, Any] = {}

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
            self._torrent_connections_limit = payload.torrent_connections_limit
            for torrent_handle in self._libtorrent_session.get_torrents():
                if torrent_handle.is_valid():
                    torrent_handle.set_max_connections(self._torrent_connections_limit)

        if payload.port is not None:
            apply_settings["listen_interfaces"] = (
                f"0.0.0.0:{payload.port},[::]:{payload.port}"
            )

        self._libtorrent_session.apply_settings(apply_settings)

    def get_torrents(self) -> list[RelayTorrent]:
        torrent_handlers = self._get_torrents()

        return [
            RelayTorrent.from_libtorrent_handle(torrent_handle)
            for torrent_handle in torrent_handlers
        ]

    def get_active_streams(self) -> list[Stream]:
        streams = []
        for torrent in self._torrents.values():
            for file in torrent.files.values():
                streams.extend(list(file.streams.values()))
        return streams

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

    def get_torrent_file(self, info_hash: str, file_index: int) -> File:
        sha1_info_hash = self._parse_info_hash(info_hash)
        file = self._torrents[sha1_info_hash].files[file_index]

        return file

    async def get_piece_data(
        self,
        torrent_handle: libtorrent.torrent_handle,
        piece_index: int,
    ) -> bytes:
        info_hash = str(torrent_handle.info_hash())
        request_key = (info_hash, piece_index)
        future: asyncio.Future[bytes] = self.loop.create_future()

        requests = self.pending_piece_requests.setdefault(request_key, [])
        requests.append(future)

        if torrent_handle.have_piece(piece_index):
            torrent_handle.read_piece(piece_index)

        try:
            return await future
        finally:
            if future in requests:
                requests.remove(future)
                if not requests:
                    self.pending_piece_requests.pop(request_key, None)

            if not future.done():
                future.cancel()

    def add_torrent(
        self,
        torrent_bytes: bytes,
        priority: int = 0,
        resume_bytes: bytes | None = None,
    ) -> RelayTorrent:
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
        torrent_handle.set_max_connections(self._torrent_connections_limit)
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

        self._torrents[torrent_info.info_hash()] = torrent

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

    def _get_torrent(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> libtorrent.torrent_handle | None:
        torrent_handle = self._libtorrent_session.find_torrent(info_hash)

        if not torrent_handle.is_valid():
            return None

        return torrent_handle

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

        del self._torrents[info_hash]

        self._libtorrent_session.remove_torrent(
            torrent_handle,
            libtorrent.options_t.delete_files,
        )

        return True

    def trigger_save_resume_data(self):
        for torrent_handle in self._libtorrent_session.get_torrents():
            if torrent_handle.is_valid():
                torrent_handle.save_resume_data(
                    libtorrent.save_resume_flags_t.flush_disk_cache
                )

    def process_alerts(self):
        alerts = self._libtorrent_session.pop_alerts()

        for alert in alerts:
            try:
                match alert:
                    case libtorrent.save_resume_data_alert():
                        try:
                            resume_data = libtorrent.bencode(
                                libtorrent.write_resume_data(alert.params)
                            )
                            torrent_handle = alert.handle
                            if torrent_handle.is_valid():
                                info_hash_str = str(torrent_handle.info_hash())

                                for callback in self.on_save_resume:
                                    try:
                                        callback(info_hash_str, resume_data)
                                    except Exception as e:
                                        logger.error(
                                            f"Hiba történt az on_save_resume eseménykezelő futtatása közben: {e}"
                                        )
                        except Exception as e:
                            logger.error(
                                f"Hiba történt a torrent visszaállítási adatok mentése közben: {e}"
                            )

                    case libtorrent.save_resume_data_failed_alert():
                        logger.error(
                            f"Hiba történt a torrent visszaállítási adatok mentése közben: {alert.message()}"
                        )

                    case libtorrent.piece_finished_alert():
                        info_hash = str(alert.handle.info_hash())
                        request_key = (info_hash, alert.piece_index)
                        if request_key in self.pending_piece_requests:
                            alert.handle.read_piece(alert.piece_index)

                        self.trigger_priority_update(info_hash)

                    case libtorrent.read_piece_alert():
                        info_hash = str(alert.handle.info_hash())
                        request_key = (info_hash, alert.piece)

                        if futures := self.pending_piece_requests.pop(
                            request_key, None
                        ):
                            has_error = alert.error and alert.error.value() != 0

                            if has_error:
                                logger.error(
                                    f"Hiba a libtorrent.read_piece_alert során: {alert.error.message()}"
                                )
                                err = Exception(alert.error.message())
                                for future in futures:
                                    if not future.done():
                                        self.loop.call_soon_threadsafe(
                                            future.set_exception, err
                                        )
                            else:
                                piece_data = bytes(alert.buffer)
                                for future in futures:
                                    if not future.done():
                                        self.loop.call_soon_threadsafe(
                                            future.set_result, piece_data
                                        )

            except Exception as e:
                logger.error(f"Hiba a {type(alert).__name__} feldolgozása közben: {e}")

    def _parse_info_hash(
        self,
        info_hash_str: str,
    ) -> libtorrent.sha1_hash:
        info_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return info_hash
