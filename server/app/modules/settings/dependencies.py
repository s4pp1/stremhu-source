from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.service import SettingsService


def create_settings_service(db: Session) -> SettingsService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    repository = SettingsRepository(db)
    return SettingsService(repository)


def get_settings_service(
    db: Annotated[Session, Depends(get_db)],
) -> SettingsService:
    """FastAPI függőség-injektáló provider a SettingsService példányosításához."""
    return create_settings_service(db)
