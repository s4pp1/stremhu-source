import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.playback_histories.models import PlaybackHistoryModel
from app.modules.torrents.models import TorrentModel
from app.modules.torrents.schemas.internal import TorrentUpdate


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

    def update(self, info_hash: str, payload: TorrentUpdate) -> TorrentModel | None:
        model = self.find_by_info_hash(info_hash)

        if model:
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(model, key, value)
            self.db.flush()

        return model

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
            TorrentModel.is_persisted.is_(False),
        )

        if not_completed_torrent_ids:
            query = query.filter(
                TorrentModel.torrent_id.not_in(not_completed_torrent_ids)
            )

        if keep_seed_seconds is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(
                seconds=keep_seed_seconds
            )

            last_played_subquery = (
                self.db.query(func.max(PlaybackHistoryModel.created_at))
                .filter(
                    PlaybackHistoryModel.indexer_id == TorrentModel.indexer_id,
                    PlaybackHistoryModel.torrent_id == TorrentModel.torrent_id,
                )
                .correlate(TorrentModel)
                .scalar_subquery()
            )

            last_played = func.coalesce(last_played_subquery, TorrentModel.created_at)
            query = query.filter(last_played < cutoff)

        return query.all()
