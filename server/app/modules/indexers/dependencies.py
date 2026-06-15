from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.indexers.service import IndexersService
from app.modules.settings.dependencies import create_settings_service
from app.modules.torrents.dependencies import create_torrents_service


def create_indexers_service(db: Session) -> IndexersService:
    indexer_accounts_service = create_indexer_accounts_service(db)
    indexer_definitions_service = get_indexer_definitions_service()
    torrents_service = create_torrents_service(db)
    settings_service = create_settings_service(db)

    return IndexersService(
        indexer_accounts_service=indexer_accounts_service,
        indexer_definitions_service=indexer_definitions_service,
        torrents_service=torrents_service,
        settings_service=settings_service,
    )


def get_indexers_service(
    db: Annotated[Session, Depends(get_db)],
) -> IndexersService:
    return create_indexers_service(db)
