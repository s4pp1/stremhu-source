from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from server.modules.filesystem.router import browse_directories, create_directory
from server.modules.filesystem.schemas.api import CreateDirectoryRequest
from server.modules.filesystem.service import FilesystemService
from server.modules.settings.schemas.internal import SystemSettings
from server.modules.users.models import UserModel


@pytest.fixture
def mock_settings_service(tmp_path: Path):
    mock = MagicMock()
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    mock.find_system.return_value = SystemSettings(downloads_dir=downloads_dir)
    return mock


def test_browse_directories_explicit_path(tmp_path: Path, mock_settings_service):
    service = FilesystemService(settings_service=mock_settings_service)

    browse_root = tmp_path / "browse_root"
    browse_root.mkdir()
    (browse_root / "folder_b").mkdir()
    (browse_root / "folder_a").mkdir()
    (browse_root / "regular_file.txt").touch()
    (browse_root / ".hidden_folder").mkdir()

    res = service.browse_directories(path=str(browse_root))

    assert res.current_path == str(browse_root.resolve())
    assert res.parent_path == (
        str(browse_root.parent.resolve()) if browse_root.parent != browse_root else None
    )

    names = [d.name for d in res.directories]
    # Check alphabetized ordering and exclusions
    assert names == ["folder_a", "folder_b"]
    assert "regular_file.txt" not in names
    assert ".hidden_folder" not in names


def test_browse_directories_default_downloads_dir(
    tmp_path: Path, mock_settings_service
):
    service = FilesystemService(settings_service=mock_settings_service)

    downloads_dir = tmp_path / "downloads"
    (downloads_dir / "sub_item").mkdir()

    res = service.browse_directories(path=None)

    assert res.current_path == str(downloads_dir.resolve())
    assert [d.name for d in res.directories] == ["sub_item"]


def test_create_directory_success(tmp_path: Path, mock_settings_service):
    service = FilesystemService(settings_service=mock_settings_service)

    created_path = service.create_directory(
        parent_path=str(tmp_path), name="my_new_folder"
    )

    assert created_path == (tmp_path / "my_new_folder").resolve()
    assert (tmp_path / "my_new_folder").is_dir()


def test_create_directory_invalid_parent(tmp_path: Path, mock_settings_service):
    service = FilesystemService(settings_service=mock_settings_service)

    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(HTTPException) as exc_info:
        service.create_directory(parent_path=str(non_existent), name="sub")

    assert exc_info.value.status_code == 400
    assert "szülő mappa nem létezik" in exc_info.value.detail


@pytest.mark.parametrize(
    "invalid_name", ["", "   ", "dir/with/slash", "dir\\backslash", "..", "."]
)
def test_create_directory_invalid_names(
    tmp_path: Path, mock_settings_service, invalid_name: str
):
    service = FilesystemService(settings_service=mock_settings_service)

    with pytest.raises(HTTPException) as exc_info:
        service.create_directory(parent_path=str(tmp_path), name=invalid_name)

    assert exc_info.value.status_code == 400
    assert "Érvénytelen mappanév" in exc_info.value.detail


def test_create_directory_already_exists(tmp_path: Path, mock_settings_service):
    service = FilesystemService(settings_service=mock_settings_service)

    (tmp_path / "existing").mkdir()
    with pytest.raises(HTTPException) as exc_info:
        service.create_directory(parent_path=str(tmp_path), name="existing")

    assert exc_info.value.status_code == 400
    assert "már létezik" in exc_info.value.detail


def test_router_endpoints(tmp_path: Path, mock_settings_service):
    service = FilesystemService(settings_service=mock_settings_service)
    admin_user = UserModel(username="admin")

    browse_root = tmp_path / "browse_root"
    browse_root.mkdir()
    (browse_root / "test_folder").mkdir()

    browse_res = browse_directories(
        filesystem_service=service,
        _=admin_user,
        path=str(browse_root),
    )
    assert browse_res.current_path == str(browse_root.resolve())
    assert [d.name for d in browse_res.directories] == ["test_folder"]

    create_res = create_directory(
        payload=CreateDirectoryRequest(
            parent_path=str(browse_root), name="added_folder"
        ),
        filesystem_service=service,
        _=admin_user,
    )
    assert create_res.path == str((browse_root / "added_folder").resolve())
    assert (browse_root / "added_folder").is_dir()
