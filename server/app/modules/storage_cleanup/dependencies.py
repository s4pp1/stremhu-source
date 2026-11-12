from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.indexer_accounts.dependencies import create_indexer_accounts_service
from app.modules.indexer_definitions.dependencies import get_indexer_definitions_service
from app.modules.relay.dependencies import get_relay_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.storage_cleanup.service import StorageCleanupService
from app.modules.torrents.dependencies import create_torrents_service


def create_storage_cleanup_service(db: Session) -> StorageCleanupService:
    return StorageCleanupService(
        settings_service=create_settings_service(db),
        indexer_accounts_service=create_indexer_accounts_service(db),
        indexer_definitions_service=get_indexer_definitions_service(),
        torrents_service=create_torrents_service(db),
        relay_service=get_relay_service(),
    )


def get_storage_cleanup_service(
    db: Annotated[Session, Depends(get_db)],
) -> StorageCleanupService:
    return create_storage_cleanup_service(db)
