from fastapi import HTTPException

from app.common.async_utils import fire_and_forget, owned_to_thread
from app.common.database import isolated_db_session, shared_read_session
from app.common.logger import logger
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.repository import TorrentFilesRepository
from app.modules.torrent_files.schemas import (
    TorrentFileIdentifier,
    TorrentFilesFilter,
    TorrentFileSnapshot,
)


class IsolatedTorrentFilesService:
    """Service elszigetelt adatbázis tranzakciókhoz"""

    def touch(
        self, identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier]
    ) -> None:
        """Azonnal elindítja a touch-ot a háttérben, de nem várja meg az eredményét."""
        fire_and_forget(owned_to_thread(self._touch, identifiers))

    def find_by_id(self, indexer_id: str, torrent_id: str) -> TorrentFileModel | None:
        """Kikeresi a .torrent fájlt, rövid életű session-ben."""
        with isolated_db_session() as local_db:
            torrent_files_repository = TorrentFilesRepository(local_db)
            torrent_file = torrent_files_repository.find_by_id(indexer_id, torrent_id)
            if torrent_file:
                local_db.expunge(torrent_file)
            return torrent_file

    def find_snapshots(
        self, identifiers: list[TorrentFileIdentifier]
    ) -> list[TorrentFileSnapshot]:
        """Session nélküli leírók rövid életű, korlátozott olvasó session-ben; a snapshot még a Session zárása előtt épül."""
        with shared_read_session() as local_db:
            return [
                TorrentFileSnapshot.from_model(torrent_file)
                for torrent_file in TorrentFilesRepository(local_db).find_list(
                    filter=TorrentFilesFilter(identifiers=identifiers)
                )
            ]

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

    def create_many(
        self, items: list[tuple[str, str, bytes]]
    ) -> list[TorrentFileModel]:
        """Több .torrent fájlt ment el egyetlen kötegelt SQLite tranzakcióban."""
        if not items:
            return []

        with isolated_db_session() as local_db:
            repo = TorrentFilesRepository(local_db)
            identifiers = [
                TorrentFileIdentifier(indexer_id=iid, torrent_id=tid)
                for iid, tid, _ in items
            ]
            existing = repo.find_list(
                filter=TorrentFilesFilter(identifiers=identifiers)
            )
            existing_map: dict[tuple[str, str], TorrentFileModel] = {
                (tf.indexer_id, tf.torrent_id): tf for tf in existing
            }

            to_insert: list[TorrentFileModel] = []
            seen: set[tuple[str, str]] = set(existing_map.keys())
            for iid, tid, t_bytes in items:
                if (iid, tid) in seen:
                    continue
                seen.add((iid, tid))
                try:
                    to_insert.append(
                        TorrentFileModel(
                            indexer_id=iid,
                            torrent_id=tid,
                            torrent_bytes=t_bytes,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Érvénytelen torrent fájl átugorva (batch): indexer: {iid}, torrent_id: {tid} ({e})"
                    )

            if to_insert:
                repo.create_many_ignore_duplicates(to_insert)

            all_models = repo.find_list(
                filter=TorrentFilesFilter(identifiers=identifiers)
            )
            for model in all_models:
                local_db.expunge(model)
            return all_models

    def _touch(
        self, identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier]
    ) -> None:
        """Frissíti a legutóbbi használati időt (last_used_at) külön, rövid életű session-ben."""
        try:
            with isolated_db_session() as local_db:
                TorrentFilesRepository(local_db).touch(identifiers)
        except Exception as e:
            logger.warning(f"Nem sikerült frissíteni a torrent használati idejét: {e}")
