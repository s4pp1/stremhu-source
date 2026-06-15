from typing import Annotated
from app.common.database import get_db
from fastapi import Depends
from app.modules.indexer_accounts.repository import IndexerAccountsRepository
from app.modules.indexer_accounts.service import IndexerAccountsService
from sqlalchemy.orm import Session


def create_indexer_accounts_service(db: Session) -> IndexerAccountsService:
    indexer_accounts_repository = IndexerAccountsRepository(db)
    return IndexerAccountsService(
        indexer_accounts_repository=indexer_accounts_repository,
    )


def get_indexer_accounts_service(
    db: Annotated[Session, Depends(get_db)],
) -> IndexerAccountsService:
    return create_indexer_accounts_service(db)
