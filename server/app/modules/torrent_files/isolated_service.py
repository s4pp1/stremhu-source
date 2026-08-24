import asyncio

from fastapi import HTTPException

from app.common.async_utils import fire_and_forget
from app.common.database import isolated_db_session
from app.common.logger import logger
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.schemas import TorrentFileIdentifier


class IsolatedTorrentFilesService:
    """Service elszigetelt adatbázis tranzakciókhoz"""

    def touch(
        self, identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier]
    ) -> None:
        """Azonnal elindítja a touch-ot a háttérben, de nem várja meg az eredményét."""
        fire_and_forget(asyncio.to_thread(self._touch, identifiers))

    def find_by_id(self, indexer_id: str, torrent_id: str) -> TorrentFileModel | None:
        """Kikeresi a .torrent fájlt, rövid életű session-ben."""
        with isolated_db_session() as local_db:
            torrent_files_repository = TorrentFilesRepository(local_db)
            torrent_file = torrent_files_repository.find_by_id(indexer_id, torrent_id)
            if torrent_file:
                local_db.expunge(torrent_file)
            return torrent_file

    def create(
        self, indexer_id: str, torrent_id: str, torrent_bytes: bytes
    ) -> TorrentFileModel:
        """Elmenti a .torrent fájlt, rövid életű session-ben."""
        with isolated_db_session() as local_db:
            torrent_files_repository = TorrentFilesRepository(local_db)

            torrent_file = torrent_files_repository.find_by_id(
                indexer_id=indexer_id,
                torrent_id=torrent_id,
            )

            if torrent_file:
                raise HTTPException(
                    status_code=409,
                    detail=f"Már létezik torrent a gyorsítótárban: {indexer_id} - {torrent_id}",
                )

            torrent_file = torrent_files_repository.create(
                TorrentFileModel(
                    indexer_id=indexer_id,
                    torrent_id=torrent_id,
                    torrent_bytes=torrent_bytes,
                )
            )
            local_db.expunge(torrent_file)
            return torrent_file

    def _touch(
        self, identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier]
    ) -> None:
        """Frissíti a legutóbbi használati időt (last_used_at) külön, rövid életű session-ben."""
        try:
            with isolated_db_session() as local_db:
                TorrentFilesRepository(local_db).touch(identifiers)
        except Exception as e:
            logger.warning(f"Nem sikerült frissíteni a torrent használati idejét: {e}")
