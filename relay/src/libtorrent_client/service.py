import logging
import os
import time
from typing import Any, Dict, List

import libtorrent as libtorrent
from config import config
from fastapi import HTTPException
from libtorrent_client.schemas import (
    UpdateSettings,
    UpdateTorrent,
)

logger = logging.getLogger(__name__)


class LibtorrentClientService:
    def __init__(self):
        self.libtorrent_session = libtorrent.session()

        alert_mask = (  # pyright: ignore[reportUnknownVariableType]
            libtorrent.alert.category_t.error_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            | libtorrent.alert.category_t.storage_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            | libtorrent.alert.category_t.status_notification  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        )

        self.libtorrent_session.apply_settings(
            {
                "alert_mask": alert_mask,
                "listen_interfaces": "0.0.0.0:6881,[::]:6881",
                "connections_limit": 200,
                "enable_dht": False,
                "enable_lsd": False,
                "auto_sequential": False,
                "peer_timeout": 10,
                "piece_extent_affinity": True,
                "piece_timeout": 5,
                "request_timeout": 5,
                "unchoke_interval": 1,
                "disk_io_write_mode": 2,
                "disk_io_read_mode": 2,
            }
        )

        self.torrent_connections_limit = 20

    def update_settings(
        self,
        payload: UpdateSettings,
    ):
        apply_settings: Dict[str, Any] = {}

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
            self.torrent_connections_limit = payload.torrent_connections_limit
            for torrent_handle in self.libtorrent_session.get_torrents():
                if torrent_handle.is_valid():
                    torrent_handle.set_max_connections(self.torrent_connections_limit)

        if payload.port is not None:
            apply_settings["listen_interfaces"] = (
                f"0.0.0.0:{payload.port},[::]:{payload.port}"
            )

        self.libtorrent_session.apply_settings(apply_settings)

        if payload.torrent_connections_limit is not None:
            self.torrent_connections_limit = payload.torrent_connections_limit

    def get_torrents(self) -> List[libtorrent.torrent_handle]:
        torrent_handlers = self.libtorrent_session.get_torrents()

        valid_torrent_handlers = [
            torrent_handler
            for torrent_handler in torrent_handlers
            if torrent_handler.is_valid()
        ]

        return valid_torrent_handlers

    def add_torrent(
        self,
        torrent_file_path: str,
        priority: int,
    ) -> libtorrent.torrent_handle:
        save_path = str(config.downloads_dir.absolute())
        resume_data_dir = config.resume_data_dir

        torrent_file_path = os.path.abspath(torrent_file_path)

        if not os.path.isfile(torrent_file_path):
            raise HTTPException(
                400, f'A(z) "{torrent_file_path}" torrent fájl nem található.'
            )

        torrent_info = libtorrent.torrent_info(torrent_file_path)
        info_hash_str = str(torrent_info.info_hash())
        resume_file_path = resume_data_dir / f"{info_hash_str}.resume"

        params = None
        if resume_file_path.exists():
            try:
                with open(resume_file_path, "rb") as f:
                    resume_data = f.read()
                    params = libtorrent.read_resume_data(resume_data)
            except Exception as e:
                logger.error(
                    f"Hiba történt a(z) {info_hash_str} torrent adatok visszaállítása közben: {e}"
                )

        if params is None:
            params = libtorrent.add_torrent_params()

        params.ti = torrent_info
        params.save_path = save_path
        params.storage_mode = libtorrent.storage_mode_t.storage_mode_sparse

        torrent_handle = self.libtorrent_session.add_torrent(params)
        torrent_handle.set_max_connections(self.torrent_connections_limit)
        torrent_handle.unset_flags(libtorrent.torrent_flags.disable_pex)

        is_valid = False

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            is_valid = torrent_handle.is_valid()
            if is_valid:
                break

            time.sleep(0.1)

        if not is_valid:
            self.libtorrent_session.remove_torrent(
                torrent_handle,
                libtorrent.options_t.delete_files,
            )
            raise HTTPException(
                500,
                f'A(z) "{torrent_file_path}" .torrent-et nem sikerült hozzáadni.',
            )

        priorities = torrent_handle.piece_priorities()
        torrent_handle.prioritize_pieces([priority] * len(priorities))

        return torrent_handle

    def get_torrent(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> libtorrent.torrent_handle | None:
        torrent_handle = self.libtorrent_session.find_torrent(info_hash)

        if not torrent_handle.is_valid():
            return None

        return torrent_handle

    def get_torrent_or_raise(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> libtorrent.torrent_handle:
        torrent_handle = self.get_torrent(
            info_hash=info_hash,
        )

        if torrent_handle is None:
            raise HTTPException(404, f'"{info_hash}" torrent nem található.')

        return torrent_handle

    def update_torrent_or_raise(
        self,
        info_hash: libtorrent.sha1_hash,
        payload: UpdateTorrent,
    ):
        torrent_handle = self.get_torrent_or_raise(
            info_hash=info_hash,
        )

        if payload.priority is not None:
            priorities = torrent_handle.piece_priorities()
            torrent_handle.prioritize_pieces([payload.priority] * len(priorities))

        return torrent_handle

    def remove_torrent(
        self,
        info_hash: libtorrent.sha1_hash,
    ):

        torrent_handle = self.get_torrent_or_raise(
            info_hash=info_hash,
        )

        self.libtorrent_session.remove_torrent(
            torrent_handle,
            libtorrent.options_t.delete_files,
        )

        info_hash_str = str(info_hash)
        resume_file_path = config.resume_data_dir / f"{info_hash_str}.resume"
        if resume_file_path.exists():
            try:
                os.remove(resume_file_path)
            except OSError as e:
                logger.error(
                    f"Hiba történt a(z) {info_hash_str} torrent visszaállítási adatok törlése közben: {e}"
                )

    def trigger_save_resume_data(self):
        for torrent_handle in self.libtorrent_session.get_torrents():
            if torrent_handle.is_valid():
                torrent_handle.save_resume_data(
                    libtorrent.save_resume_flags_t.flush_disk_cache
                )

    def process_alerts(self):
        alerts = self.libtorrent_session.pop_alerts()
        resume_data_dir = config.resume_data_dir
        os.makedirs(resume_data_dir, exist_ok=True)

        for alert in alerts:
            if isinstance(alert, libtorrent.save_resume_data_alert):
                try:
                    resume_data = libtorrent.bencode(
                        libtorrent.write_resume_data(alert.params)
                    )
                    torrent_handle = alert.handle
                    if torrent_handle.is_valid():
                        info_hash_str = str(torrent_handle.info_hash())
                        resume_file = resume_data_dir / f"{info_hash_str}.resume"

                        with open(resume_file, "wb") as f:
                            f.write(resume_data)
                except Exception as e:
                    logger.error(
                        f"Hiba történt a torrent visszaállítási adatok mentése közben: {e}"
                    )
            elif isinstance(alert, libtorrent.save_resume_data_failed_alert):
                logger.error(
                    f"Hiba történt a torrent visszaállítási adatok mentése közben: {alert.message()}"
                )

    def parse_info_hash(
        self,
        info_hash_str: str,
    ) -> libtorrent.sha1_hash:
        info_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return info_hash
