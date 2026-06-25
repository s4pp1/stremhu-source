from fastapi import HTTPException, status

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_accounts.repository import IndexerAccountsRepository
from app.modules.indexer_accounts.schemas import (
    IndexerAccountCreate,
    IndexerAccountUpdate,
)
from app.modules.preference_definitions.service import PreferenceDefinitionsService


class IndexerAccountsService:
    def __init__(
        self,
        indexer_accounts_repository: IndexerAccountsRepository,
        preference_definitions_service: PreferenceDefinitionsService,
    ):
        self._indexer_accounts_repository = indexer_accounts_repository
        self._preference_definitions_service = preference_definitions_service

    def create(self, payload: IndexerAccountCreate) -> IndexerAccountModel:
        indexer_account = self.find_by_id(payload.indexer_id)

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
        return self._ensure_exists(indexer_account)

    def update(
        self,
        indexer_id: str,
        payload: IndexerAccountUpdate,
    ) -> IndexerAccountModel:
        model = self._indexer_accounts_repository.update(indexer_id, payload)
        return self._ensure_exists(model)

    def delete(
        self,
        indexer_id: str,
    ) -> None:
        self._indexer_accounts_repository.delete(indexer_id)
        self._preference_definitions_service.remove_attribute_from_all(indexer_id)

    def _ensure_exists(self, model: IndexerAccountModel | None) -> IndexerAccountModel:
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nincs létező indexer fiók!",
            )
        return model
