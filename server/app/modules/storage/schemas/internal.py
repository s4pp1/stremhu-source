from enum import Enum

from pydantic import BaseModel


class StorageModeEnum(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class StorageStatus(BaseModel):
    mode: StorageModeEnum
    # Letöltésekre használható teljes kapacitás (auto: foglalt + lemez szabad helye)
    capacity_bytes: int
    # Torrentek által ténylegesen foglalt hely
    used_bytes: int
    # Még szabadon használható hely
    free_bytes: int
    # A futó letöltések még hiányzó, kijelölt bájtjai
    pending_bytes: int
    # Mindig szabadon tartott biztonsági tartalék
    reserve_bytes: int
    # A letöltési könyvtárat tartalmazó lemez adatai
    disk_total_bytes: int
    disk_free_bytes: int
    # Seedben tartott, de hely esetén törölhető torrentek
    evictable_count: int
    evictable_bytes: int
