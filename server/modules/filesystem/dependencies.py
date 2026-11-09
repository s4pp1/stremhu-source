from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from server.common.database import get_db
from server.modules.filesystem.service import FilesystemService
from server.modules.settings.dependencies import create_settings_service


def create_filesystem_service(db: Session) -> FilesystemService:
    settings_service = create_settings_service(db)
    return FilesystemService(settings_service=settings_service)


def get_filesystem_service(
    db: Annotated[Session, Depends(get_db)],
) -> FilesystemService:
    return create_filesystem_service(db)
