import libtorrent as libtorrent
from fastapi import HTTPException, status

from app.common.constants import PRIO_0, PRIO_1
from app.common.logger import logger
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.indexer_definitions.service import IndexerDefinitionsService
from app.modules.relay.service import RelayService
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.repository import TorrentRepository
from app.modules.torrents.schemas.internal import TorrentUpdate, TorrentWithRelay


class TorrentsService:
    def __init__(
        self,
        torrent_repository: TorrentRepository,
        torrent_files_service: TorrentFilesService,
        indexer_accounts_service: IndexerAccountsService,
        indexer_definitions_service: IndexerDefinitionsService,
        relay_service: RelayService,
    ):
        self._torrent_repository = torrent_repository
        self._torrent_files_service = torrent_files_service
        self._indexer_accounts_service = indexer_accounts_service
        self._indexer_definitions_service = indexer_definitions_service
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

        priority = self._get_priority(torrent)

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

        torrent_model = self._torrent_repository.update(info_hash, payload)
        torrent_model = self._ensure_exists(torrent_model)

        if "full_download" in payload.model_fields_set:
            if payload.full_download is False:
                indexer_definition = self._indexer_definitions_service.get_by_id(
                    torrent_model.indexer_id
                )
                if indexer_definition.requires_full_download:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Nem lehetséges a '{indexer_definition.name}' esetében kikapcsolni a teljes letöltést!",
                    )

            priority = self._get_priority(torrent_model)

            sha1_hash = self.parse_info_hash(info_hash)
            torrent = self._relay_service._torrents.get(sha1_hash)
            if torrent:
                torrent.update_default_priority(priority)

        relay_torrent = self._relay_service.get_torrent_or_raise(info_hash)
        return TorrentWithRelay(
            torrent=torrent_model,
            relay=relay_torrent,
        )

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
        self._torrent_repository.update(
            info_hash=info_hash,
            payload=TorrentUpdate(
                resume_bytes=resume_bytes,
            ),
        )

    def restore_torrents(self) -> None:
        torrents = self._torrent_repository.find()

        for torrent in torrents:
            try:
                priority = self._get_priority(torrent)
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

    def _ensure_exists(self, model: TorrentModel | None) -> TorrentModel:
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A torrent nem található!",
            )
        return model

    def _get_priority(self, torrent: TorrentModel) -> int:
        if torrent.full_download is not None:
            return PRIO_1 if torrent.full_download else PRIO_0

        indexer_account = self._indexer_accounts_service.get_by_id(torrent.indexer_id)
        return PRIO_1 if indexer_account.download_full_torrent else PRIO_0
