import logging
import os
import time
from typing import Any, Dict, List

import libtorrent as libtorrent
from fastapi import HTTPException
from torrents.schemas import (
    AddTorrent,
    UpdateSettings,
)

logger = logging.getLogger(__name__)


class LibtorrentService:
    def __init__(self):
        self.libtorrent_session = libtorrent.session()
        self.libtorrent_session.apply_settings(
            {
                "listen_interfaces": "0.0.0.0:6881",
                "connections_limit": 200,
                "enable_dht": False,
                "enable_lsd": False,
                "auto_sequential": False,
                "peer_timeout": 30,
                "piece_extent_affinity": True,
                "piece_timeout": 20,
                "request_timeout": 15,
                "unchoke_interval": 10,
            }
        )

        self.torrent_connections_limit = 20

    def update_settings(
        self,
        payload: UpdateSettings,
    ):
        apply_settings: Dict[str, Any] = {}

        if payload.download_rate_limit is not None:
            apply_settings["download_rate_limit"] = payload.download_rate_limit

        if payload.upload_rate_limit is not None:
            apply_settings["upload_rate_limit"] = payload.upload_rate_limit

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
            apply_settings["listen_interfaces"] = f"0.0.0.0:{payload.port}"

        self.libtorrent_session.apply_settings(apply_settings)

        if payload.torrent_connections_limit is not None:
            self.torrent_connections_limit = payload.torrent_connections_limit

    def get_torrents(self) -> List[libtorrent.torrent_handle]:
        torrent_handlers = self.libtorrent_session.get_torrents()
        return torrent_handlers

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
        torrent_handle = self.get_torrent(info_hash=info_hash)

        if torrent_handle is None:
            raise HTTPException(404, f'"{info_hash}" torrent nem található.')

        return torrent_handle

    def add_torrent(
        self,
        req: AddTorrent,
    ) -> libtorrent.torrent_handle:
        save_path = os.path.abspath(req.save_path)
        torrent_file_path = os.path.abspath(req.torrent_file_path)

        if not os.path.isfile(torrent_file_path):
            raise HTTPException(
                400, f'A(z) "{torrent_file_path}" torrent fájl nem található.'
            )

        torrent_info = libtorrent.torrent_info(torrent_file_path)

        os.makedirs(save_path, exist_ok=True)

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

            time.sleep(1.0)

        if not is_valid:
            self.libtorrent_session.remove_torrent(
                torrent_handle,
                libtorrent.options_t.delete_files,
            )
            raise HTTPException(
                500,
                f'A(z) "{torrent_file_path}" .torrent-et nem sikerült hozzáadni.',
            )

        return torrent_handle

    def remove_torrent(
        self,
        info_hash: libtorrent.sha1_hash,
    ) -> libtorrent.sha1_hash:
        torrent_handle = self.get_torrent_or_raise(
            info_hash=info_hash,
        )

        self.libtorrent_session.remove_torrent(
            torrent_handle,
            libtorrent.options_t.delete_files,
        )

        return info_hash

    def parse_info_hash(
        self,
        info_hash_str: str,
    ) -> libtorrent.sha1_hash:
        sha1_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return sha1_hash
