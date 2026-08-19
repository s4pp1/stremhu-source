import datetime

from sqlalchemy import and_, false, or_
from sqlalchemy.orm import Session, joinedload

from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier, TorrentFilesFilter

TOUCH_THROTTLE = datetime.timedelta(minutes=15)


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
            if filter.identifiers is not None:
                conditions = [
                    and_(
                        TorrentFileModel.indexer_id == identifier.indexer_id,
                        TorrentFileModel.torrent_id == identifier.torrent_id,
                    )
                    for identifier in filter.identifiers
                ]
                query = query.filter(or_(*conditions) if conditions else false())
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

    def delete_expired(self, expiration_date: datetime.datetime) -> int:
        result = (
            self.db.query(TorrentFileModel)
            .filter(
                TorrentFileModel.last_used_at < expiration_date,
                ~TorrentFileModel.torrent.has(),
            )
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return result

    def touch(
        self,
        identifiers: TorrentFileIdentifier | list[TorrentFileIdentifier],
    ) -> None:
        if not identifiers:
            return

        identifiers_list = (
            identifiers if isinstance(identifiers, list) else [identifiers]
        )

        now = datetime.datetime.now()
        stale_filter = and_(
            or_(
                *[
                    and_(
                        TorrentFileModel.indexer_id == identifier.indexer_id,
                        TorrentFileModel.torrent_id == identifier.torrent_id,
                    )
                    for identifier in identifiers_list
                ]
            ),
            TorrentFileModel.last_used_at <= now - TOUCH_THROTTLE,
        )

        has_stale = (
            self.db.query(TorrentFileModel.indexer_id).filter(stale_filter).first()
            is not None
        )
        if not has_stale:
            return

        self.db.query(TorrentFileModel).filter(stale_filter).update(
            {TorrentFileModel.last_used_at: now},
            synchronize_session=False,
        )
