import os
from pathlib import Path

from fastapi import HTTPException

from server.modules.filesystem.schemas.api import (
    BrowseDirectoriesResponse,
    DirectoryEntry,
)
from server.modules.settings.service import SettingsService


class FilesystemService:
    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service

    def browse_directories(self, path: str | None = None) -> BrowseDirectoriesResponse:
        if path:
            target = Path(path).expanduser().resolve()
        else:
            system_settings = self._settings_service.find_system()
            if (
                system_settings
                and system_settings.downloads_dir
                and system_settings.downloads_dir.exists()
            ):
                target = system_settings.downloads_dir.resolve()
            else:
                target = Path.home().resolve()

        if not target.exists() or not target.is_dir():
            if target.parent.exists() and target.parent.is_dir():
                target = target.parent
            else:
                target = Path.home().resolve()

        parent_path = str(target.parent) if target.parent != target else None

        directories: list[DirectoryEntry] = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    try:
                        if entry.name.startswith("."):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            directories.append(
                                DirectoryEntry(
                                    name=entry.name,
                                    path=str(Path(entry.path).resolve()),
                                )
                            )
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass

        directories.sort(key=lambda x: x.name.lower())

        return BrowseDirectoriesResponse(
            current_path=str(target),
            parent_path=parent_path,
            directories=directories,
        )

    def create_directory(self, parent_path: str, name: str) -> Path:
        parent = Path(parent_path).expanduser().resolve()
        if not parent.exists() or not parent.is_dir():
            raise HTTPException(400, "A szülő mappa nem létezik.")

        clean_name = name.strip().strip("/").strip("\\")
        if (
            not clean_name
            or "/" in clean_name
            or "\\" in clean_name
            or clean_name in (".", "..")
        ):
            raise HTTPException(400, "Érvénytelen mappanév.")

        new_dir = parent / clean_name
        try:
            new_dir.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            raise HTTPException(400, "A megadott nevű mappa már létezik.")
        except Exception as e:
            raise HTTPException(400, f"Nem sikerült létrehozni a mappát: {e}")

        return new_dir.resolve()
