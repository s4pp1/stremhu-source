import functools

from app.common.database import db_session
from app.modules.indexer_accounts.repository import IndexerAccountsRepository
from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin
from app.modules.indexer_definitions.service import IndexerDefinitionsService


class IndexerAccountStorage:
    def get_credentials(self, indexer_id: str) -> IndexerDefinitionLogin | None:
        with db_session() as db:
            repository = IndexerAccountsRepository(db)
            user = repository.find_by_id(indexer_id)
            if not user:
                return None
            return IndexerDefinitionLogin(
                username=user.username,
                password=user.password,
                cookies=user.cookies,
            )

    def save_cookies(self, indexer_id: str, cookies: dict[str, str]) -> None:
        with db_session() as db:
            repository = IndexerAccountsRepository(db)
            repository.update_cookies(indexer_id, cookies)


@functools.lru_cache(maxsize=1)
def get_indexer_definitions_service() -> IndexerDefinitionsService:
    indexer_account_storage = IndexerAccountStorage()
    return IndexerDefinitionsService(indexer_account_storage)
