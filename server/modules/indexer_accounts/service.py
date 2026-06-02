from fastapi import HTTPException, status
from modules.indexer_accounts.models import IndexerAccountModel
from modules.indexer_accounts.repository import IndexerAccountsRepository
from modules.indexer_accounts.schemas import IndexerAccountCreate, IndexerAccountUpdate


class IndexerAccountsService:
    def __init__(
        self,
        indexer_accounts_repository: IndexerAccountsRepository,
    ):
        self._indexer_accounts_repository = indexer_accounts_repository

    def create(self, payload: IndexerAccountCreate) -> IndexerAccountModel:
        indexer_account = self.get_by_id(payload.indexer_id)

        if indexer_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Már létezik indexer account!",
            )
        return self._indexer_accounts_repository.create(payload)

    def find_list(self) -> list[IndexerAccountModel]:
        return self._indexer_accounts_repository.find_list()

    def find_by_id(self, indexer_id: str) -> IndexerAccountModel | None:
        return self._indexer_accounts_repository.find_by_id(indexer_id)

    def get_by_id(self, indexer_id: str) -> IndexerAccountModel:
        indexer_account = self.find_by_id(indexer_id)
        if indexer_account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nem található indexer!",
            )
        return indexer_account

    def update(
        self,
        indexer_id: str,
        payload: IndexerAccountUpdate,
    ) -> None:
        indexer_account = self.get_by_id(indexer_id)
        if payload.hit_and_run is not None:
            indexer_account.hit_and_run = payload.hit_and_run
        if payload.keep_seed_seconds is not None:
            indexer_account.keep_seed_seconds = payload.keep_seed_seconds
        if payload.download_full_torrent is not None:
            indexer_account.download_full_torrent = payload.download_full_torrent

        self._indexer_accounts_repository.update(indexer_account)
