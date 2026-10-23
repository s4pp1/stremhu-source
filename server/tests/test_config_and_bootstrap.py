from pathlib import Path

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


def test_config_is_dev_flags(monkeypatch):
    import sys

    from server.config import Config

    # Default is False
    monkeypatch.setattr(sys, "argv", ["stremhu", "--host-ip", "192.168.1.200"])
    monkeypatch.delenv("IS_DEV", raising=False)
    assert Config(_env_file=None).is_dev is False

    # CLI --is-dev
    monkeypatch.setattr(
        sys,
        "argv",
        ["stremhu", "--host-ip", "192.168.1.200", "--is-dev"],
    )
    assert Config(_env_file=None).is_dev is True

    # ENV IS_DEV=true
    monkeypatch.setattr(sys, "argv", ["stremhu", "--host-ip", "192.168.1.200"])
    monkeypatch.setenv("IS_DEV", "true")
    assert Config(_env_file=None).is_dev is True


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


def test_bootstrap_port_config_override(monkeypatch):
    from server.config import config

    monkeypatch.setattr(config, "port", 8888)

    boot_config = bootstrap_app()
    assert boot_config.port == 8888


def test_save_system_downloads_dir_forbidden_when_overridden(monkeypatch):
    import pytest
    from fastapi import HTTPException

    from server.config import config

    monkeypatch.setattr(config, "downloads_dir", Path("/downloads"))

    with db_session() as db:
        service = create_settings_service(db)
        with pytest.raises(HTTPException) as exc_info:
            service.save_system(SystemSettingsUpdate(downloads_dir=Path("/other")))
        assert exc_info.value.status_code == 403


def test_save_system_downloads_dir_allowed_when_not_overridden(monkeypatch):
    from server.config import config

    monkeypatch.setattr(config, "downloads_dir", None)
    monkeypatch.setattr(config, "default_downloads_dir", Path("/default"))

    with db_session() as db:
        service = create_settings_service(db)
        updated = service.save_system(
            SystemSettingsUpdate(downloads_dir=Path("/allowed_new_dir"))
        )
        assert updated.downloads_dir == Path("/allowed_new_dir")


def test_config_downloads_dir_required(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.delenv("DEFAULT_DOWNLOADS_DIR", raising=False)
    monkeypatch.delenv("DOWNLOADS_DIR", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Config(
            _env_file=None,
            host_ip="192.168.1.100",
            system_dir=Path("/tmp/data"),
            client_path=Path("client/dist"),
            default_downloads_dir=None,
            downloads_dir=None,
        )
    assert "DEFAULT_DOWNLOADS_DIR" in str(exc_info.value)


def test_config_downloads_dir_overridden_status():
    cfg_default = Config(
        host_ip="192.168.1.100",
        system_dir=Path("/tmp/data"),
        client_path=Path("client/dist"),
        default_downloads_dir=Path("/default"),
        downloads_dir=None,
    )
    assert cfg_default.is_downloads_dir_overridden is False

    cfg_overridden = Config(
        host_ip="192.168.1.100",
        system_dir=Path("/tmp/data"),
        client_path=Path("client/dist"),
        downloads_dir=Path("/downloads"),
    )
    assert cfg_overridden.is_downloads_dir_overridden is True


def test_get_app_url_uses_config_port(monkeypatch):
    from server.config import config

    monkeypatch.setattr(config, "port", 7075)
    with db_session() as db:
        service = create_settings_service(db)
        url = service.get_app_url()
        assert ":7075" in url


def test_system_settings_response_path_serialization():
    from server.modules.settings.schemas.api import SystemSettingsResponse
    from server.modules.settings.schemas.internal import SystemSettings
    from server.modules.system.schemas.api import SystemStatusResponse
    from server.modules.system.schemas.internal import SystemStatus

    system_settings = SystemSettings(downloads_dir=Path("/Users/test/Downloads"))
    settings_resp = SystemSettingsResponse.model_validate(system_settings)
    assert settings_resp.downloads_dir == Path("/Users/test/Downloads")
    dumped_settings = settings_resp.model_dump(mode="json", by_alias=True)
    assert dumped_settings["downloadsDir"] == "/Users/test/Downloads"

    status = SystemStatus(
        configured=True,
        version="0.0.0",
        app_url="https://stremhu.local:7070",
        host_ip="192.168.1.100",
        port=7070,
        downloads_dir=Path("/Users/test/Downloads"),
        is_reverse_proxy=False,
        is_downloads_dir_overridden=False,
    )
    status_resp = SystemStatusResponse.model_validate(status)
    assert status_resp.downloads_dir == Path("/Users/test/Downloads")
    dumped_status = status_resp.model_dump(mode="json", by_alias=True)
    assert dumped_status["downloadsDir"] == "/Users/test/Downloads"
