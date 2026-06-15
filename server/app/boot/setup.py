import sys
from pathlib import Path

from alembic.config import Config
from rich.console import Console

from alembic import command
from app.config import config

console = Console()
err_console = Console(stderr=True)


def setup_directories():
    console.print("🔄 Szükséges könyvtárstruktúra ellenőrzése", style="bold cyan")

    config.database_dir.mkdir(parents=True, exist_ok=True)
    config.openapi_dir.mkdir(parents=True, exist_ok=True)
    config.client_path.mkdir(parents=True, exist_ok=True)

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def run_migrations():
    console.print("🔄 Adatbázis-migrációk ellenőrzése", style="bold cyan")

    try:
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        err_console.print(
            f"[bold red][HIBA] Nem sikerült lefutattatni a migrációkat: {e}[/]"
        )
        sys.exit(1)
