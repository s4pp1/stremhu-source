import server.common.models  # noqa: F401
from server.boot.network import ensure_network_settings
from server.boot.schemas import BootNetworkConfig
from server.boot.settings import ensure_default_settings
from server.boot.setup import (
    run_migrations,
    setup_system_dir,
)
from server.common.logger import setup_logger


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
