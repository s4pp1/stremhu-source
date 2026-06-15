from typing import Annotated
from app.common.database import get_db
from fastapi import Depends
from app.modules.preferences.repository import PreferencesRepository
from app.modules.preferences.service import PreferencesService
from sqlalchemy.orm import Session


def create_preferences_service(
    db: Session,
) -> PreferencesService:
    preferences_repository = PreferencesRepository(db)
    return PreferencesService(preferences_repository)


def get_preferences_service(
    db: Annotated[Session, Depends(get_db)],
) -> PreferencesService:
    return create_preferences_service(db)
