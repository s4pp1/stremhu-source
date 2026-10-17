from pathlib import Path
from unittest.mock import PropertyMock, patch

from core.boot.bootstrap import bootstrap_app
from core.common.database import db_session
from core.config import Config
from core.modules.settings.dependencies import create_settings_service
from core.modules.settings.schemas.internal import SystemSettingsUpdate


def test_system_settings_downloads_dir(tmp_path: Path):
    with db_session() as db:
        service = create_settings_service(db)
        custom_dir = str(tmp_path / "custom_downloads")

        # Mentés DB-be
        updated = service.save_system(SystemSettingsUpdate(downloads_dir=custom_dir))
        assert updated.downloads_dir == custom_dir

        # Visszaolvasás DB-ből
        fetched = service.get_system()
        assert fetched.downloads_dir == custom_dir


def test_config_downloads_dir_hierarchy(tmp_path: Path):
    test_config = Config(host_ip="192.168.1.100")

    # 1. Alapértelmezett állapot
    with patch.object(test_config, "downloads_dir_override", None):
        with patch.object(
            Config,
            "base_downloads_dir",
            new_callable=PropertyMock,
            return_value=tmp_path / "default_downloads",
        ):
            # Ha DB-ben nincs beállítva
            with db_session() as db:
                service = create_settings_service(db)
                service.save_system(SystemSettingsUpdate(downloads_dir=None))

            assert test_config.downloads_dir == tmp_path / "default_downloads"

            # 2. Ha az adatbázisban be van állítva
            db_dir = tmp_path / "db_downloads"
            with db_session() as db:
                service = create_settings_service(db)
                service.save_system(SystemSettingsUpdate(downloads_dir=str(db_dir)))

            assert test_config.downloads_dir == db_dir

            # 3. Ha az ENV (override) felülbírálja a DB-t
            env_dir = tmp_path / "env_downloads"
            test_config.downloads_dir_override = str(env_dir)
            assert test_config.downloads_dir == env_dir


def test_config_data_dir_override(tmp_path: Path):
    override_path = str(tmp_path / "custom_data")
    test_config = Config(
        host_ip="192.168.1.100",
        data_dir_override=override_path,
    )
    assert test_config.base_data_dir == Path(override_path)


def test_config_cli_args_parsing(monkeypatch):
    import sys

    from core.config import Config

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "stremhu",
            "--host-ip",
            "192.168.1.200",
            "--data-dir=/tmp/cli_data",
            "--unknown-flag",
            "val",
        ],
    )
    test_config = Config()
    assert test_config.host_ip == "192.168.1.200"
    assert test_config.data_dir_override == "/tmp/cli_data"


def test_config_cli_overrides_env_and_defaults(monkeypatch, tmp_path: Path):
    import sys

    from server.run import parse_args

    cli_dir = str(tmp_path / "cli_data")
    env_dir = str(tmp_path / "env_data")

    # 1. Core csak a CLI-t veszi figyelembe, közvetlen ENV-et nem
    monkeypatch.setenv("DATA_DIR", env_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        ["stremhu", "--data-dir", cli_dir, "--host-ip=192.168.1.222"],
    )

    test_config = Config()
    assert test_config.data_dir_override == cli_dir
    assert test_config.base_data_dir == Path(cli_dir)
    assert test_config.host_ip == "192.168.1.222"

    # 2. A server/settings és server/run feloldja az ENV-et, ha CLI-n nincs megadva
    monkeypatch.setattr(sys, "argv", ["stremhu"])
    server_args = parse_args()
    assert server_args.data_dir == env_dir

    from server.settings import ServerSettings, apply_server_settings

    settings = ServerSettings()
    assert settings.data_dir == env_dir

    dummy_cfg = Config()
    apply_server_settings(settings, target_config=dummy_cfg)
    assert dummy_cfg.data_dir_override == env_dir


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
    from core.config import config

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

    from core.config import Config

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
