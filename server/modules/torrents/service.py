import logging

import libtorrent as libtorrent
from common.constants import PRIO_0, PRIO_1
from fastapi import HTTPException
from modules.relay.service import RelayService
from modules.torrent_files.models import TorrentFileModel
from modules.torrent_files.service import TorrentFilesService
from modules.torrents.models import TorrentModel
from modules.torrents.repository import TorrentRepository
from modules.torrents.schemas import TorrentPair, TorrentUpdate

logger = logging.getLogger(__name__)


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

    def get_torrents(self) -> list[TorrentPair]:
        torrents = self._torrent_repository.find()
        relay_torrents = self._relay_service.get_torrents()

        relay_torrent_map = {
            relay_torrent.info_hash: relay_torrent for relay_torrent in relay_torrents
        }

        result: list[TorrentPair] = []
        for torrent in torrents:
            if torrent.torrent_file and torrent.torrent_file.info_hash:
                info_hash = torrent.torrent_file.info_hash
                if info_hash in relay_torrent_map:
                    result.append(
                        TorrentPair(torrent=torrent, relay=relay_torrent_map[info_hash])
                    )

        return result

    def create_from_torrent_file(self, torrent_file: TorrentFileModel) -> TorrentPair:
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

        return TorrentPair(torrent=torrent, relay=relay_torrent)

    def get_one(
        self,
        indexer_id: str,
        torrent_id: str,
    ) -> TorrentPair | None:
        torrent = self._torrent_repository.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )
        if torrent is None:
            return None

        relay_torrent = self._relay_service.get_torrent_or_raise(torrent.info_hash)
        return TorrentPair(torrent=torrent, relay=relay_torrent)

    def get_or_raise(
        self,
        info_hash: str,
    ) -> TorrentPair:
        torrent = self._torrent_repository.find_by_info_hash(info_hash)
        if torrent is None:
            raise HTTPException(404, "A torrent nem található")

        relay_torrent = self._relay_service.get_torrent_or_raise(info_hash)

        return TorrentPair(torrent=torrent, relay=relay_torrent)

    def update(
        self,
        info_hash: str,
        payload: TorrentUpdate,
    ) -> TorrentPair:
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
        return TorrentPair(torrent=persisted, relay=relay_torrent)

    def delete(
        self,
        info_hash: str,
    ):
        self._torrent_repository.delete(info_hash=info_hash)
        self._relay_service.delete_torrent(info_hash=info_hash)

    def delete_all_by_indexer(self, indexer_id: str) -> None:
        torrents = self._torrent_repository.find_by_indexer(indexer_id)
        for torrent in torrents:
            self.delete(torrent.info_hash)
        self._torrent_files_service.delete_all_by_indexer(indexer_id)

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
        """Rendszerindítást követően betölti/visszaállítja a torrenteket az adatbázisból a libtorrent-be."""
        logger.info("🔄 Torrentek visszaállítása az adatbázisból...")
        torrents = self._torrent_repository.find()

        count = 0
        for torrent in torrents:
            if not torrent.torrent_file or not torrent.torrent_file.torrent_bytes:
                logger.warning(
                    "⚠️ Nem sikerült visszaállítani a torrentet (%s): hiányzik a .torrent fájl!",
                    torrent.info_hash,
                )
                continue

            try:
                # Meghatározzuk a kezdeti prioritást
                # (Ha full_download be van kapcsolva, akkor PRIO_1, különben PRIO_0)
                priority = PRIO_1 if torrent.full_download else PRIO_0

                self._relay_service.add_torrent(
                    torrent_bytes=torrent.torrent_file.torrent_bytes,
                    priority=priority,
                    resume_bytes=torrent.resume_bytes,
                )
                count += 1
            except Exception as e:
                logger.error(
                    "❌ Hiba a torrent (%s) visszaállítása közben: %s",
                    torrent.info_hash,
                    e,
                )

        logger.info("✅ Sikeresen visszaállítva %d/%d torrent.", count, len(torrents))
