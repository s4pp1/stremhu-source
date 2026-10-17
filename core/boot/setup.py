from alembic import command
from alembic.config import Config

from core.common.logger import logger
from core.common.paths import get_core_dir
from core.config import config


def setup_system_dir():
    config.database_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def run_migrations():
    try:
        core_dir = get_core_dir()
        alembic_ini_path = core_dir / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(core_dir / "alembic"))
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.exception("Nem sikerült lefutattatni a migrációkat.")
        raise RuntimeError(f"Adatbázis migrációs hiba: {e}") from e
