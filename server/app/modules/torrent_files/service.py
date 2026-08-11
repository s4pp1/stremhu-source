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

    def run_retention_cleanup(self, retention_seconds: int | None = None) -> None:
        """Törli a gyorsítótárból (adatbázisból) a lejárt és inaktív torrent rekordokat (LRU).

        Ha retention_seconds = 0, minden inaktív torrentet töröl.
        """
        if retention_seconds is None:
            retention_seconds = 7 * 24 * 3600

        now = datetime.datetime.now()
        expiration_date = now - datetime.timedelta(seconds=retention_seconds)

        try:
            deleted_count = self._torrent_files_repository.delete_expired(
                expiration_date
            )
            if deleted_count > 0:
                logger.info(
                    f"🧹 Törölve {deleted_count} elavult torrent a gyorsítótárból."
                )
        except Exception:
            logger.exception(
                "Nem sikerült törölni az elavult torrenteket az adatbázisból."
            )
