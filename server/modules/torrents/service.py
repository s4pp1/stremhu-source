import libtorrent as libtorrent
from common.constants import PRIO_0, PRIO_1
from common.logger import logger
from fastapi import HTTPException
from modules.relay.service import RelayService
from modules.torrent_files.models import TorrentFileModel
from modules.torrent_files.service import TorrentFilesService
from modules.torrents.models import TorrentModel
from modules.torrents.repository import TorrentRepository
from modules.torrents.schemas.internal import TorrentUpdate, TorrentWithRelay


class TorrentsService:
    def __init__(
        self,
        torrent_repository: TorrentRepository,
        torrent_files_service: TorrentFilesService,
        relay_service: RelayService,
    ):
        self._torrent_repository = torrent_repository
        self._torrent_files_service = torrent_files_service
        self._relay_service = relay_service

    def create_from_torrent_file(
        self,
        torrent_file: TorrentFileModel,
    ) -> TorrentWithRelay:
        torrent_model = TorrentModel(
            indexer_id=torrent_file.indexer_id,
            torrent_id=torrent_file.torrent_id,
            info_hash=torrent_file.info.info_hash,
        )

        torrent = self._torrent_repository.create(torrent_model)

        priority = PRIO_1 if torrent.full_download else PRIO_0

        relay_torrent = self._relay_service.add_torrent(
            torrent_bytes=torrent.torrent_file.torrent_bytes,
            priority=priority,
        )

        return TorrentWithRelay(torrent=torrent, relay=relay_torrent)

    def get_torrents(self) -> list[TorrentWithRelay]:
        torrents = self._torrent_repository.find()
        relay_torrents = self._relay_service.get_torrents()

        relay_torrent_map = {
            relay_torrent.info_hash: relay_torrent for relay_torrent in relay_torrents
        }

        result: list[TorrentWithRelay] = []
        for torrent in torrents:
            if torrent.torrent_file and torrent.torrent_file.info_hash:
                info_hash = torrent.torrent_file.info_hash
                if info_hash in relay_torrent_map:
                    result.append(
                        TorrentWithRelay(
                            torrent=torrent, relay=relay_torrent_map[info_hash]
                        )
                    )

        return result

    def find_by_id(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> TorrentWithRelay | None:
        torrent = self._torrent_repository.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )
        if torrent is None:
            return None

        relay_torrent = self._relay_service.get_torrent_or_raise(torrent.info_hash)
        return TorrentWithRelay(torrent=torrent, relay=relay_torrent)

    def get_by_info_hash(
        self,
        info_hash: str,
    ) -> TorrentWithRelay:
        torrent = self._torrent_repository.find_by_info_hash(info_hash)
        if torrent is None:
            raise HTTPException(404, "A torrent nem található")

        relay_torrent = self._relay_service.get_torrent_or_raise(info_hash)

        return TorrentWithRelay(torrent=torrent, relay=relay_torrent)

    def update(
        self,
        info_hash: str,
        payload: TorrentUpdate,
    ) -> TorrentWithRelay:
        persisted = self._torrent_repository.find_by_info_hash(info_hash)
        if persisted is None:
            raise HTTPException(404, "A torrent nem található")

        if payload.is_persisted is not None:
            persisted.is_persisted = payload.is_persisted

        if payload.download_full_torrent is not None:
            persisted.full_download = payload.download_full_torrent

            priority = PRIO_1 if payload.download_full_torrent else PRIO_0
            sha1_hash = self.parse_info_hash(info_hash)
            torrent = self._relay_service._torrents.get(sha1_hash)
            if torrent:
                torrent.update_default_priorities(priority)

        self._torrent_repository.update(persisted)

        relay_torrent = self._relay_service.get_torrent_or_raise(info_hash)
        return TorrentWithRelay(torrent=persisted, relay=relay_torrent)

    def bulk_update_by_indexer_id(
        self,
        indexer_id: str,
        payload: TorrentUpdate,
    ) -> None:
        torrents = self._torrent_repository.find_by_indexer_id(indexer_id)

        for torrent in torrents:
            self.update(torrent.info_hash, payload)

    def delete(
        self,
        info_hash: str,
    ):
        self._torrent_repository.delete(info_hash=info_hash)
        self._relay_service.delete_torrent(info_hash=info_hash)

    def delete_by_indexer_id(self, indexer_id: str) -> None:
        torrents = self._torrent_repository.find_by_indexer_id(indexer_id)
        for torrent in torrents:
            self.delete(torrent.info_hash)
        self._torrent_files_service.delete_by_indexer_id(indexer_id)

    def cleanup_tracker_torrents(
        self,
        indexer_id: str,
        keep_seed_seconds: int | None,
        not_completed_torrent_ids: list[str] | None,
    ) -> None:
        torrents = self._torrent_repository.find_for_cleanup(
            indexer_id=indexer_id,
            keep_seed_seconds=keep_seed_seconds,
            not_completed_torrent_ids=not_completed_torrent_ids,
        )
        for torrent in torrents:
            self.delete(torrent.info_hash)

    def parse_info_hash(self, info_hash_str: str) -> libtorrent.sha1_hash:
        sha1_hash = libtorrent.sha1_hash(bytes.fromhex(info_hash_str))
        return sha1_hash

    def save_resume_data(self, info_hash: str, resume_bytes: bytes) -> None:
        persisted = self._torrent_repository.find_by_info_hash(info_hash)
        if persisted:
            persisted.resume_bytes = resume_bytes
            self._torrent_repository.update(persisted)

    def restore_torrents(self) -> None:
        torrents = self._torrent_repository.find()

        for torrent in torrents:
            try:
                priority = PRIO_1 if torrent.full_download else PRIO_0
                self._relay_service.add_torrent(
                    torrent_bytes=torrent.torrent_file.torrent_bytes,
                    priority=priority,
                    resume_bytes=torrent.resume_bytes,
                )
            except Exception as e:
                logger.error(
                    "❌ Hiba a torrent (%s) visszaállítása közben: %s",
                    torrent.info_hash,
                    e,
                )
