from pathlib import Path
from unittest.mock import PropertyMock

from server.boot.bootstrap import bootstrap_app
from server.common.database import db_session
from server.config import Config
from server.modules.settings.dependencies import create_settings_service
from server.modules.settings.schemas.internal import SystemSettingsUpdate


def test_system_settings_downloads_dir(tmp_path: Path):
    with db_session() as db:
        service = create_settings_service(db)
        custom_dir = str(tmp_path / "custom_downloads")

        # Mentés DB-be
        updated = service.save_system(
            SystemSettingsUpdate(downloads_dir=Path(custom_dir))
        )
        assert updated.downloads_dir == Path(custom_dir)

        # Visszaolvasás DB-ből
        fetched = service.get_system()
        assert fetched.downloads_dir == Path(custom_dir)


def test_config_system_dir_override(tmp_path: Path):
    override_path = tmp_path / "custom_data"
    test_config = Config(
        host_ip="192.168.1.100",
        system_dir=override_path,
    )
    assert test_config.system_dir == override_path
    assert test_config.database_dir == override_path / "database"


def test_config_cli_args_parsing(monkeypatch):
    import sys

    from server.config import Config

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "stremhu",
            "--host-ip",
            "192.168.1.200",
            "--system-dir=/tmp/cli_data",
            "--unknown-flag",
            "val",
        ],
    )
    test_config = Config()
    assert test_config.host_ip == "192.168.1.200"
    assert test_config.system_dir == Path("/tmp/cli_data")
    assert test_config.reload is False


def test_config_reload_flag(monkeypatch):
    import sys

    from server.config import Config

    monkeypatch.setattr(
        sys,
        "argv",
        ["stremhu", "--host-ip", "192.168.1.200", "--reload"],
    )
    test_config = Config()
    assert test_config.reload is True


def test_config_env_file_loading(tmp_path: Path):
    from server.config import Config

    env_file = tmp_path / ".env"
    env_file.write_text("HOST_IP=192.168.1.150\nRELOAD=true\nUNKNOWN_CUSTOM_VAR=xyz\n")
    cfg = Config(_env_file=env_file)
    assert cfg.host_ip == "192.168.1.150"
    assert cfg.reload is True


def test_config_cli_overrides_env_and_defaults(monkeypatch, tmp_path: Path):
    import sys

    cli_dir = str(tmp_path / "cli_data")
    env_dir = str(tmp_path / "env_data")

    # 1. CLI felülbírálja az ENV-et
    monkeypatch.setenv("SYSTEM_DIR", env_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        ["stremhu", "--system-dir", cli_dir, "--host-ip=192.168.1.222"],
    )

    test_config = Config()
    assert test_config.system_dir == Path(cli_dir)
    assert test_config.host_ip == "192.168.1.222"

    # 2. Ha nincs CLI, az ENV érvényesül
    monkeypatch.setattr(sys, "argv", ["stremhu", "--host-ip=192.168.1.222"])
    test_config_env = Config()
    assert test_config_env.system_dir == Path(env_dir)


def test_bootstrap_app():
    # A bootstrap futtatása tesztkörnyezetben
    boot_config = bootstrap_app()
    assert boot_config is not None
    assert boot_config.network_settings is not None
    assert boot_config.port is not None


def test_bootstrap_port_from_system_settings():
    with db_session() as db:
        service = create_settings_service(db)
        service.save_system(SystemSettingsUpdate(port=7777))

    boot_config = bootstrap_app()
    assert boot_config.port == 7777

    # Visszaállítjuk
    with db_session() as db:
        service = create_settings_service(db)
        service.save_system(SystemSettingsUpdate(port=7070))


def test_bootstrap_port_env_override(monkeypatch):
    from server.config import config

    monkeypatch.setattr(config, "port", 8888)
    monkeypatch.setattr(Config, "is_port_overridden", PropertyMock(return_value=True))

    boot_config = bootstrap_app()
    assert boot_config.port == 8888

    # Ellenőrizzük, hogy az adatbázisba is beíródott az ENV portja
    with db_session() as db:
        service = create_settings_service(db)
        assert service.get_system().port == 8888


def test_save_system_port_forbidden_when_overridden(monkeypatch):
    import pytest
    from fastapi import HTTPException

    from server.config import Config

    monkeypatch.setattr(Config, "is_port_overridden", PropertyMock(return_value=True))

    with db_session() as db:
        service = create_settings_service(db)
        with pytest.raises(HTTPException) as exc_info:
            service.save_system(SystemSettingsUpdate(port=9999))
        assert exc_info.value.status_code == 403


def test_get_app_url_uses_system_settings_port():
    with db_session() as db:
        service = create_settings_service(db)
        service.save_system(SystemSettingsUpdate(port=7075))
        url = service.get_app_url()
        assert ":7075" in url

        # Visszaállítás
        service.save_system(SystemSettingsUpdate(port=7070))
