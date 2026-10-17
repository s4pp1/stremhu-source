from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.preferences.repository import PreferencesRepository
from core.modules.preferences.service import PreferencesService


def create_preferences_service(
    db: Session,
) -> PreferencesService:
    preferences_repository = PreferencesRepository(db)
    return PreferencesService(preferences_repository)


def get_preferences_service(
    db: Annotated[Session, Depends(get_db)],
) -> PreferencesService:
    return create_preferences_service(db)
