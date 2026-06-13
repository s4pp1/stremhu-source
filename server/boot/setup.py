import sys

from alembic import command
from alembic.config import Config
from config import config
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def setup_directories():
    console.print("🔄 Szükséges könyvtárstruktúra ellenőrzése", style="bold cyan")

    config.openapi_dir.mkdir(parents=True, exist_ok=True)
    config.client_path.mkdir(parents=True, exist_ok=True)

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.certificates_dir.mkdir(parents=True, exist_ok=True)


def run_migrations():
    console.print("🔄 Adatbázis-migrációk ellenőrzése", style="bold cyan")

    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        err_console.print(
            f"[bold red][HIBA] Nem sikerült lefutattatni a migrációkat: {e}[/]"
        )
        sys.exit(1)
