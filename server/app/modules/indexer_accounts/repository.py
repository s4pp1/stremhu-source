from sqlalchemy.orm import Session, joinedload

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.schemas import (
    IndexerAccountCreate,
    IndexerAccountUpdate,
)


class IndexerAccountsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: IndexerAccountCreate) -> IndexerAccountModel:
        model = IndexerAccountModel(
            indexer_id=payload.indexer_id,
            username=payload.username,
            password=payload.password,
            download_full_torrent=payload.download_full_torrent,
            hit_and_run=payload.hit_and_run,
            keep_seed_seconds=payload.keep_seed_seconds,
            cookies=payload.cookies,
        )

        self.db.add(model)
        self.db.flush()

        return model

    def find_list(self) -> list[IndexerAccountModel]:
        return (
            self.db.query(IndexerAccountModel)
            .options(joinedload(IndexerAccountModel.indexer_definition))
            .all()
        )

    def find_by_id(self, indexer_id: str) -> IndexerAccountModel | None:
        return (
            self.db.query(IndexerAccountModel)
            .options(joinedload(IndexerAccountModel.indexer_definition))
            .filter_by(indexer_id=indexer_id)
            .first()
        )

    def update(
        self,
        indexer_id: str,
        payload: IndexerAccountUpdate,
    ) -> IndexerAccountModel | None:
        model = self.find_by_id(indexer_id)

        if model:
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(model, key, value)
            self.db.flush()

        return model

    def delete(self, indexer_id: str) -> None:
        self.db.query(IndexerAccountModel).filter_by(indexer_id=indexer_id).delete()

    def update_cookies(self, indexer_id: str, cookies: dict) -> None:
        model = self.find_by_id(indexer_id)
        if model:
            model.cookies = cookies
            self.db.flush()
