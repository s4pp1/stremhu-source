import sys
from pathlib import Path

from alembic.config import Config
from rich.console import Console
from rich.panel import Panel

from alembic import command
from app.common.logger import logger
from app.config import config
from app.legacy_migration.source import (
    SourceError,
    database_kind,
    find_legacy_database,
)


def setup_directories():
    config.database_dir.mkdir(parents=True, exist_ok=True)
    config.client_path.mkdir(parents=True, exist_ok=True)

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def exit_if_legacy_data():
    """Leáll, ha az adatkönyvtárban egy régi (v0.22 vagy korábbi) verzió adatai vannak.

    Enélkül a v0.20–v0.22 adatbázison az alembic migráció elhasalna, a v0.17–v0.19
    mappaszerkezet mellett pedig csendben egy üres új adatbázis jönne létre.
    """
    legacy_db = find_legacy_database(config.base_data_dir)
    if legacy_db is None:
        return

    new_db = config.database_dir / "app.db"
    try:
        new_db_kind = database_kind(new_db)
    except SourceError:
        new_db_kind = None
    if new_db_kind == "current":
        logger.warning(
            "Az adatkönyvtárban egy régi verzió adatbázisa is található (%s), "
            "ezt a rendszer nem használja.",
            legacy_db,
        )
        return

    console = Console()
    console.print(
        Panel(
            f"Az adatkönyvtárban egy régi (v0.22 vagy korábbi) StremHU Source adatai "
            f"vannak ([bold]{legacy_db.relative_to(config.base_data_dir)}[/bold]).\n\n"
            "A felhasználók, API kulcsok, indexer fiókok, preferenciák és torrentek "
            "átvihetők a migrációs eszközzel (a szerver leállított állapotában):\n\n"
            "  [cyan]docker compose run --rm stremhu-source "
            "python -m app.legacy_migration --dry-run[/cyan]\n"
            "  [cyan]docker compose run --rm stremhu-source "
            "python -m app.legacy_migration[/cyan]\n\n"
            "Tiszta telepítéshez helyezd át a régi mappákat az adatkönyvtárból.",
            title="[bold yellow]Régi verzió adatai[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )
    sys.exit(1)


def run_migrations():
    try:
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        logger.exception("Nem sikerült lefutattatni a migrációkat.")
        sys.exit(1)
