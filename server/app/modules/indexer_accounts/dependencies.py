from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexer_accounts.repository import IndexerAccountsRepository
from app.modules.indexer_accounts.service import IndexerAccountsService
from app.modules.preference_definitions.dependencies import (
    create_preference_definitions_service,
)


def create_indexer_accounts_service(db: Session) -> IndexerAccountsService:
    indexer_accounts_repository = IndexerAccountsRepository(db)
    preference_definitions_service = create_preference_definitions_service(db)

    return IndexerAccountsService(
        indexer_accounts_repository=indexer_accounts_repository,
        preference_definitions_service=preference_definitions_service,
    )


def get_indexer_accounts_service(
    db: Annotated[Session, Depends(get_db)],
) -> IndexerAccountsService:
    return create_indexer_accounts_service(db)
