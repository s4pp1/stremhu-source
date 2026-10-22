from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from server.common.database import get_db
from server.modules.attributes.dependencies import create_attributes_service
from server.modules.preference_definitions.dependencies import (
    create_preference_definitions_service,
)
from server.modules.user_preference_definitions.repository import (
    UserPreferenceDefinitionsRepository,
)
from server.modules.user_preference_definitions.service import (
    UserPreferenceDefinitionsService,
)


def create_user_preference_definitions_service(
    db: Session,
) -> UserPreferenceDefinitionsService:
    user_preference_definitions_repository = UserPreferenceDefinitionsRepository(db)
    preference_definitions_service = create_preference_definitions_service(db)
    attributes_service = create_attributes_service(db)

    return UserPreferenceDefinitionsService(
        user_preference_definitions_repository,
        preference_definitions_service,
        attributes_service,
    )


def get_user_preference_definitions_service(
    db: Annotated[Session, Depends(get_db)],
) -> UserPreferenceDefinitionsService:
    return create_user_preference_definitions_service(db)
