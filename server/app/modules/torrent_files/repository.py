import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier, TorrentFilesFilter


class TorrentFilesRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, model: TorrentFileModel) -> TorrentFileModel:
        self.db.add(model)
        self.db.flush()
        return model

    def find_list(
        self,
        filter: TorrentFilesFilter | None = None,
    ) -> list[TorrentFileModel]:
        query = self.db.query(TorrentFileModel).options(
            joinedload(TorrentFileModel.indexer_account)
        )

        if filter:
            if filter.indexer_id:
                query = query.filter_by(indexer_id=filter.indexer_id)
            if filter.torrent_id:
                query = query.filter_by(torrent_id=filter.torrent_id)
            if filter.identifiers:
                conditions = [
                    and_(
                        TorrentFileModel.indexer_id == identifier.indexer_id,
                        TorrentFileModel.torrent_id == identifier.torrent_id,
                    )
                    for identifier in filter.identifiers
                ]
                query = query.filter(or_(*conditions))
            if filter.exclude_persisted:
                query = query.filter(~TorrentFileModel.torrent.has())

        return query.all()

    def find_by_id(self, indexer_id: str, torrent_id: str) -> TorrentFileModel | None:
        return (
            self.db.query(TorrentFileModel)
            .filter_by(
                indexer_id=indexer_id,
                torrent_id=torrent_id,
            )
            .first()
        )

    def find_by_info_hash(self, info_hash: str) -> TorrentFileModel | None:
        return self.db.query(TorrentFileModel).filter_by(info_hash=info_hash).first()

    def delete(self, model: TorrentFileModel) -> None:
        self.db.delete(model)
        self.db.flush()

    def touch(
        self,
        identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier],
    ) -> None:
        """Frissíti a megadott .torrent fájl(ok) legutóbbi használati idejét (last_used_at) az adatbázisban."""
        if not identifiers:
            return

        identifiers_list = (
            identifiers if isinstance(identifiers, list) else [identifiers]
        )

        records = self.find_list(TorrentFilesFilter(identifiers=identifiers_list))

        if records:
            now = datetime.datetime.now()
            for record in records:
                record.last_used_at = now
            self.db.flush()
