import core.common.models  # noqa: F401
from core.boot.network import ensure_network_settings
from core.boot.schemas import BootNetworkConfig
from core.boot.settings import ensure_default_settings
from core.boot.setup import (
    run_migrations,
    setup_system_dir,
)
from core.common.logger import setup_logger


def bootstrap_app() -> BootNetworkConfig:
    """Egységes alkalmazás-indítási folyamat (Docker és Desktop környezetben is):

    1. Logger inicializálása
    2. Rendszerkönyvtárak létrehozása
    3. Munkamenet titkosítási kulcs biztosítása (session_secret)
    4. Adatbázis migrációk lefutattatása (Alembic)
    5. Alapértelmezett rendszer- és relay-beállítások biztosítása
    6. Hálózati konfiguráció és SSL certifikátok beállítása
    """
    setup_logger()
    setup_system_dir()
    run_migrations()
    ensure_default_settings()
    return ensure_network_settings()
