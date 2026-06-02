from modules.indexer_accounts.models import IndexerAccountModel
from modules.indexer_accounts.schemas import IndexerAccountCreate
from sqlalchemy.orm import Session


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
        return self.db.query(IndexerAccountModel).all()

    def find_by_id(self, indexer_id: str) -> IndexerAccountModel | None:
        return (
            self.db.query(IndexerAccountModel).filter_by(indexer_id=indexer_id).first()
        )

    def update(self, model: IndexerAccountModel) -> IndexerAccountModel:
        self.db.add(model)
        self.db.flush()
        return model

    def delete(self, model: IndexerAccountModel) -> None:
        self.db.delete(model)
        self.db.flush()

    def update_cookies(self, indexer_id: str, cookies: dict) -> None:
        model = self.find_by_id(indexer_id)
        if model:
            model.cookies = cookies
            self.db.flush()
