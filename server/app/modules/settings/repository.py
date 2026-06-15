from sqlalchemy.orm import Session

from app.modules.settings.enums import SettingsKeyEnum
from app.modules.settings.models import SettingModel


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_one(self, key: str) -> SettingModel | None:
        return self.db.query(SettingModel).filter(SettingModel.key == key).first()

    def save(self, setting_key: SettingsKeyEnum, value: dict) -> SettingModel:
        record = self.find_one(setting_key.value)
        if record:
            record.value = value
        else:
            record = SettingModel(key=setting_key.value, value=value)
            self.db.add(record)
        self.db.flush()
        return record
