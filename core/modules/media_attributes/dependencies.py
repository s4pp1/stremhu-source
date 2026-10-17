from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.media_attributes.repository import MediaAttributesRepository
from core.modules.media_attributes.service import MediaAttributesService
from core.modules.preference_definitions.dependencies import (
    create_preference_definitions_service,
)


def create_media_attributes_service(db: Session) -> MediaAttributesService:
    repository = MediaAttributesRepository(db)
    preference_definitions_service = create_preference_definitions_service(db)
    return MediaAttributesService(
        repository=repository,
        preference_definitions_service=preference_definitions_service,
    )


def get_media_attributes_service(
    db: Annotated[Session, Depends(get_db)],
) -> MediaAttributesService:
    return create_media_attributes_service(db)
