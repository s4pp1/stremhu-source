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

        alert_mask = (  # pyright: ignore[reportUnknownVariableType]
            libtorrent.alert.category_t.error_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            | libtorrent.alert.category_t.storage_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            | libtorrent.alert.category_t.status_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        )

        self._libtorrent_session.apply_settings(
            {
                "alert_mask": alert_mask,
                "listen_interfaces": f"0.0.0.0:{config.libtorrent_port},[::]:{config.libtorrent_port}",
                "connections_limit": 200,
                "enable_dht": False,
                "enable_lsd": False,
                "auto_sequential": False,
                "peer_timeout": 10,
                "piece_extent_affinity": True,
                "piece_timeout": 5,
                "request_timeout": 5,
                "unchoke_interval": 1,
                "disk_io_write_mode": 1,
                "disk_io_read_mode": 1,
                "active_downloads": -1,
                "active_seeds": -1,
                "active_limit": -1,
            }
        )

        self._torrent_connections_limit = 20
        self._torrents: dict[libtorrent.sha1_hash, Torrent] = {}

        # Event hooks for resume data management (Observer Pattern)
        self.on_save_resume: list[Callable[[str, bytes], None]] = []

    async def priority_manager_loop(self):
        while True:
            torrents = list(self._torrents.values())
            for torrent in torrents:
                await asyncio.to_thread(torrent.priority_manager)
            await asyncio.sleep(0.1)

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
            if isinstance(alert, libtorrent.save_resume_data_alert):
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
            elif isinstance(alert, libtorrent.save_resume_data_failed_alert):
                logger.error(
                    f"Hiba történt a torrent visszaállítási adatok mentése közben: {alert.message()}"
                )

    def _parse_info_hash(
        self,
        info_hash_str: str,
    ) -> libtorrent.sha1_hash:
        info_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return info_hash
