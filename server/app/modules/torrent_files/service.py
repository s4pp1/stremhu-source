import datetime

from fastapi import HTTPException

from app.common.logger import logger
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.schemas import TorrentFileIdentifier, TorrentFilesFilter


class TorrentFilesService:
    def __init__(
        self,
        torrent_files_repository: TorrentFilesRepository,
    ):
        self._torrent_files_repository = torrent_files_repository

    def create(
        self,
        indexer_id: str,
        torrent_id: str,
        torrent_bytes: bytes,
    ) -> TorrentFileModel:
        """Elmenti a .torrent fájl bájtjait az adatbázisba."""
        torrent_file = self.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )

        if torrent_file:
            raise HTTPException(
                status_code=409,
                detail=f"Már létezik torrent a gyorsítótárban: {indexer_id} - {torrent_id}",
            )

        return self._torrent_files_repository.create(
            TorrentFileModel(
                indexer_id=indexer_id,
                torrent_id=torrent_id,
                torrent_bytes=torrent_bytes,
            )
        )

    def find_list(
        self, filter: TorrentFilesFilter | None = None
    ) -> list[TorrentFileModel]:
        return self._torrent_files_repository.find_list(filter)

    def find_by_id(self, indexer_id: str, torrent_id: str) -> TorrentFileModel | None:
        return self._torrent_files_repository.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )

    def find_by_info_hash(self, info_hash: str) -> TorrentFileModel | None:
        return self._torrent_files_repository.find_by_info_hash(info_hash)

    def touch(
        self,
        identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier],
    ) -> None:
        """Frissíti a megadott .torrent fájl(ok) legutóbbi használati idejét (last_used_at) az adatbázisban."""
        self._torrent_files_repository.touch(identifiers)

    def get_by_id(self, indexer_id: str, torrent_id: str) -> TorrentFileModel:
        record = self.find_by_id(indexer_id, torrent_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Nincs ilyen torrent a gyorsítótárban: {indexer_id} - {torrent_id}",
            )
        return record

    def delete(self, indexer_id: str, torrent_id: str) -> None:
        """Töröl egy konkrét gyorsítótárazott .torrent rekordot az adatbázisból."""
        record = self._torrent_files_repository.find_by_id(
            indexer_id=indexer_id,
            torrent_id=torrent_id,
        )
        if record:
            try:
                self._torrent_files_repository.delete(record)
                logger.info(
                    f"🧹 Torrent fájl törölve az adatbázisból: {indexer_id} - {torrent_id}"
                )
            except Exception as e:
                logger.error(
                    f"Hiba történt a(z) {indexer_id} - {torrent_id} rekord törlése során: {e}"
                )

    def delete_by_indexer_id(
        self,
        indexer_id: str,
    ) -> None:
        """Törli az indexer összes inaktív .torrent rekordját az adatbázisból."""
        torrent_files = self._torrent_files_repository.find_list(
            TorrentFilesFilter(
                indexer_id=indexer_id,
                exclude_persisted=True,
            )
        )
        if not torrent_files:
            return

        for torrent_file in torrent_files:
            try:
                self._torrent_files_repository.delete(torrent_file)
            except Exception as e:
                logger.error(
                    f"Nem sikerült törölni a(z) {torrent_file.indexer_id} - {torrent_file.torrent_id} rekordot: {e}"
                )

    def run_retention_cleanup(self, retention_seconds: int | None = None) -> None:
        """Törli a gyorsítótárból (adatbázisból) a lejárt és inaktív torrent rekordokat (LRU).

        Ha retention_seconds = 0, minden inaktív torrentet töröl.
        """
        if retention_seconds is None:
            retention_seconds = 7 * 24 * 3600

        now = datetime.datetime.now()

        torrent_files = self._torrent_files_repository.find_list(
            filter=TorrentFilesFilter(
                exclude_persisted=True,
            )
        )

        for torrent_file in torrent_files:
            elapsed_seconds = (now - torrent_file.last_used_at).total_seconds()
            is_expired = elapsed_seconds > retention_seconds

            if is_expired:
                try:
                    self._torrent_files_repository.delete(torrent_file)
                except Exception:
                    logger.exception(
                        f"Nem sikerült törölni a(z) {torrent_file.indexer_id} - {torrent_file.torrent_id} elavult torrentet az adatbázisból."
                    )
