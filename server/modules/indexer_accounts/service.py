from fastapi import HTTPException, status
from modules.indexer_accounts.models import IndexerAccountModel
from modules.indexer_accounts.repository import IndexerAccountsRepository
from modules.indexer_accounts.schemas import IndexerAccountCreate


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

    def get_by_id(self, indexer_definition_id: str) -> IndexerAccountModel | None:
        return self._indexer_accounts_repository.find_by_id(indexer_definition_id)

    def get_by_id_or_raise(self, indexer_definition_id: str) -> IndexerAccountModel:
        indexer_account = self.get_by_id(indexer_definition_id)
        if indexer_account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nem található indexer!",
            )
        return indexer_account

    def get_list(self) -> list[IndexerAccountModel]:
        return list(self._indexer_accounts_repository.find_all())
