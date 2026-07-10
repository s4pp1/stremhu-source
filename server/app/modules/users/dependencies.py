from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.attribute_exclusions.dependencies import (
    create_attribute_exclusions_service,
)
from app.modules.media_attributes.dependencies import (
    create_media_attributes_service,
)
from app.modules.preferences.dependencies import create_preferences_service
from app.modules.users.repository import UsersRepository
from app.modules.users.service import UsersService


def create_users_service(db: Session) -> UsersService:
    users_repository = UsersRepository(db)
    attribute_exclusions_service = create_attribute_exclusions_service(db)
    media_attributes_service = create_media_attributes_service(db)
    preferences_service = create_preferences_service(db)

    return UsersService(
        users_repository=users_repository,
        attribute_exclusions_service=attribute_exclusions_service,
        media_attributes_service=media_attributes_service,
        preferences_service=preferences_service,
    )


def get_users_service(
    db: Annotated[Session, Depends(get_db)],
) -> UsersService:
    return create_users_service(db)
