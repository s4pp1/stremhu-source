from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.media_attributes.repository import MediaAttributesRepository
from app.modules.media_attributes.service import MediaAttributesService


def create_media_attributes_service(db: Session) -> MediaAttributesService:
    repository = MediaAttributesRepository(db)
    return MediaAttributesService(repository)


def get_media_attributes_service(
    db: Annotated[Session, Depends(get_db)],
) -> MediaAttributesService:
    return create_media_attributes_service(db)
