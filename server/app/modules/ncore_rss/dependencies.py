from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.ncore_rss.repository import NcoreRssRepository
from app.modules.ncore_rss.service import NcoreRssService


def create_ncore_rss_service(db: Session) -> NcoreRssService:
    return NcoreRssService(
        repository=NcoreRssRepository(db),
        indexer_accounts_service=create_indexer_accounts_service(db),
        indexer_definitions_service=get_indexer_definitions_service(),
    )


def get_ncore_rss_service(
    db: Annotated[Session, Depends(get_db)],
) -> NcoreRssService:
    return create_ncore_rss_service(db)
