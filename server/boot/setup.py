from alembic import command
from alembic.config import Config

from server.common.logger import logger
from server.common.paths import get_server_dir
from server.config import config


def setup_system_dir():
    config.database_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def run_migrations():
    try:
        server_dir = get_server_dir()
        alembic_ini_path = server_dir / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(server_dir / "alembic"))
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.exception("Nem sikerült lefutattatni a migrációkat.")
        raise RuntimeError(f"Adatbázis migrációs hiba: {e}") from e
