from common.database import get_db
from fastapi import Depends
from modules.settings.repository import SettingsRepository
from modules.settings.service import SettingsService
from sqlalchemy.orm import Session


def create_settings_service(db: Session) -> SettingsService:
    """Hozzárendeli a szervizt egy háttérfeladat vagy HTTP kérés adatbázis munkamenetéhez."""
    repository = SettingsRepository(db)
    return SettingsService(repository)


def get_settings_service(
    db: Session = Depends(get_db),
) -> SettingsService:
    """FastAPI függőség-injektáló provider a SettingsService példányosításához."""
    return create_settings_service(db)
