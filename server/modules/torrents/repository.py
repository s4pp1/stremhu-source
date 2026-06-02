import datetime

from modules.torrents.models import TorrentModel
from sqlalchemy.orm import Session


class TorrentRepository:
    def __init__(self, db: Session):
        self.db = db

    def find(self) -> list[TorrentModel]:
        return self.db.query(TorrentModel).all()

    def find_by_id(self, indexer_id: str, torrent_id: str) -> TorrentModel | None:
        return (
            self.db.query(TorrentModel)
            .filter_by(indexer_id=indexer_id, torrent_id=torrent_id)
            .first()
        )

    def create(self, persisted_torrent: TorrentModel) -> TorrentModel:
        self.db.add(persisted_torrent)
        self.db.flush()

        return persisted_torrent

    def find_by_info_hash(self, info_hash: str) -> TorrentModel | None:
        return self.db.query(TorrentModel).filter_by(info_hash=info_hash).first()

    def update(self, persisted_torrent: TorrentModel) -> TorrentModel:
        self.db.add(persisted_torrent)
        self.db.flush()

        return persisted_torrent

    def delete(self, info_hash: str) -> None:
        self.db.query(TorrentModel).filter_by(info_hash=info_hash).delete()

    def find_by_indexer_id(self, indexer_id: str) -> list[TorrentModel]:
        return self.db.query(TorrentModel).filter_by(indexer_id=indexer_id).all()

    def find_for_cleanup(
        self,
        indexer_id: str,
        keep_seed_seconds: int | None = None,
        not_completed_torrent_ids: list[str] | None = None,
    ) -> list[TorrentModel]:
        query = self.db.query(TorrentModel).filter(
            TorrentModel.indexer_id == indexer_id,
            TorrentModel.is_persisted._is(False),
        )

        if not_completed_torrent_ids:
            query = query.filter(
                TorrentModel.torrent_id.not_in(not_completed_torrent_ids)
            )

        if keep_seed_seconds is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(
                seconds=keep_seed_seconds
            )
            query = query.filter(TorrentModel.last_played_at < cutoff)

        return query.all()
