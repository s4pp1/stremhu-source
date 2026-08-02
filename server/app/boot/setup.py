import sys
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.common.logger import logger
from app.config import config


def setup_directories():
    config.database_dir.mkdir(parents=True, exist_ok=True)
    config.client_path.mkdir(parents=True, exist_ok=True)

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def run_migrations():
    try:
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        logger.exception("Nem sikerült lefutattatni a migrációkat.")
        sys.exit(1)
