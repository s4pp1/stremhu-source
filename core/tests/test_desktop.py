from pytest import MonkeyPatch

from desktop.core.assets import create_tray_icon
from desktop.core.signals import AppStatus, DesktopSignals
from desktop.ui.tray import TrayController


def test_tray_controller_state_transitions(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("desktop.ui.tray.show_error", lambda title, msg: None)

    controller = TrayController()
    assert controller.status == AppStatus.STARTING
    assert not controller.is_running()

    # Build menu in STARTING state
    menu_starting = controller.build_menu()
    assert menu_starting is not None

    # Transition to RUNNING
    controller.set_running()
    assert controller.status == AppStatus.RUNNING
    assert controller.is_running()
    menu_running = controller.build_menu()
    assert menu_running is not None

    # Transition to ERROR
    controller.set_error("Test failure message")
    assert controller.status == AppStatus.ERROR
    assert not controller.is_running()
    assert controller.error_message == "Test failure message"
    menu_error = controller.build_menu()
    assert menu_error is not None


def test_create_tray_qicon():
    for status in [AppStatus.STARTING, AppStatus.RUNNING, AppStatus.ERROR]:
        icon = create_tray_icon(status)
        assert icon is not None
        assert not icon.isNull()


def test_signals_integration(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("desktop.ui.tray.show_error", lambda title, msg: None)

    signals = DesktopSignals()
    controller = TrayController(signals=signals)

    assert controller.status == AppStatus.STARTING

    # Emit RUNNING via Qt Signal
    signals.status_changed.emit(AppStatus.RUNNING)
    assert controller.status == AppStatus.RUNNING
    assert controller.is_running()

    # Emit error message via Qt Signal
    signals.error_occurred.emit("Signal error")
    assert controller.status == AppStatus.ERROR
    assert controller.error_message == "Signal error"


def test_server_process_manager_attach_to_existing(monkeypatch: MonkeyPatch):
    from desktop.core.runner import ServerProcessManager

    signals = DesktopSignals()
    manager = ServerProcessManager(signals=signals)

    # Port is already open (e.g. running in another terminal / debugger)
    monkeypatch.setattr("desktop.core.runner.is_server_port_open", lambda port: True)

    manager.start()
    assert manager.is_external is True
    assert manager.process is None

    # Check status remains running
    manager._check_status()
    assert not manager._stopping

    # Stop manager does not kill external process
    manager.stop()
    assert manager._stopping
    assert manager.process is None


def test_server_process_manager_spawn_child(monkeypatch: MonkeyPatch):
    from unittest.mock import MagicMock

    from desktop.core.runner import ServerProcessManager

    signals = DesktopSignals()
    manager = ServerProcessManager(signals=signals)

    # Port is initially closed
    monkeypatch.setattr("desktop.core.runner.is_server_port_open", lambda port: False)

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    spawn_cmd = []

    def mock_popen(cmd, *args, **kwargs):
        nonlocal spawn_cmd
        spawn_cmd = cmd
        return mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    manager.start()
    assert manager.is_external is False
    assert manager.process is not None
    assert manager.process.poll() is None
    assert "--host-ip" in spawn_cmd

    # Check status while running
    manager._check_status()
    assert not manager._stopping

    # Stop manager terminates child process
    manager.stop()
    assert manager._stopping
    assert manager.process is None
    mock_process.terminate.assert_called_once()


def test_server_process_manager_frozen_mode(monkeypatch: MonkeyPatch):
    import sys
    from unittest.mock import MagicMock

    from desktop.core.runner import ServerProcessManager

    signals = DesktopSignals()
    manager = ServerProcessManager(signals=signals)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr("desktop.core.runner.is_server_port_open", lambda port: False)

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    spawn_cmd = []

    def mock_popen(cmd, *args, **kwargs):
        nonlocal spawn_cmd
        spawn_cmd = cmd
        return mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    manager.start()
    assert manager.process is not None
    assert "--core" in spawn_cmd
    assert "--host-ip" in spawn_cmd

    manager.stop()
    assert manager._stopping
    mock_process.terminate.assert_called_once()


def test_server_process_manager_port_collision_resolution(monkeypatch: MonkeyPatch):
    from unittest.mock import MagicMock

    from core.common.database import db_session
    from core.config import config
    from core.modules.settings.dependencies import create_settings_service
    from core.modules.settings.schemas.internal import SystemSettingsUpdate
    from desktop.core.runner import ServerProcessManager

    signals = DesktopSignals()
    manager = ServerProcessManager(signals=signals)

    monkeypatch.setattr("desktop.core.runner.is_server_port_open", lambda port: False)

    # Szimuláljuk, hogy a 7070 foglalt, de a 7071 szabad
    def fake_is_port_in_use(port: int) -> bool:
        return port == 7070

    monkeypatch.setattr("desktop.core.runner.is_port_in_use", fake_is_port_in_use)

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_process)

    # Biztosítjuk, hogy a DB-ben 7070 az induló port
    with db_session() as db:
        service = create_settings_service(db)
        service.save_system(SystemSettingsUpdate(port=7070))

    config.port = 7070
    try:
        manager.start()

        assert manager.port == 7071
        assert config.port == 7071
        with db_session() as db:
            service = create_settings_service(db)
            assert service.get_system().port == 7071

        assert manager.process is not None
        manager.stop()
    finally:
        with db_session() as db:
            service = create_settings_service(db)
            service.save_system(SystemSettingsUpdate(port=7070))
        config.port = 7070


def test_get_local_ip():
    import ipaddress

    from desktop.core.network import get_local_ip

    ip = get_local_ip()
    assert ip is not None
    parsed = ipaddress.ip_address(ip)
    assert parsed.version == 4


def test_get_local_ip_selects_highest_traffic_interface(monkeypatch):
    import socket
    from collections import namedtuple

    from desktop.core.network import get_local_ip

    Addr = namedtuple("Addr", ["family", "address"])
    Stats = namedtuple("Stats", ["isup", "speed", "flags"])
    IO = namedtuple("IO", ["bytes_sent", "bytes_recv"])

    mock_addrs = {
        "en0": [Addr(family=socket.AF_INET, address="192.168.1.100")],
        "en1": [Addr(family=socket.AF_INET, address="192.168.1.200")],
        "utun0": [Addr(family=socket.AF_INET, address="10.8.0.2")],
    }
    mock_stats = {
        "en0": Stats(isup=True, speed=100, flags="up,broadcast"),
        "en1": Stats(isup=True, speed=1000, flags="up,broadcast"),
        "utun0": Stats(isup=True, speed=0, flags="up,pointopoint"),
    }
    mock_io = {
        "en0": IO(bytes_sent=1000, bytes_recv=1000),  # 2000 total
        "en1": IO(bytes_sent=50000, bytes_recv=50000),  # 100000 total (highest)
        "utun0": IO(
            bytes_sent=999999, bytes_recv=999999
        ),  # pont-pont VPN, ki kell zárnia
    }

    monkeypatch.setattr("psutil.net_if_addrs", lambda: mock_addrs)
    monkeypatch.setattr("psutil.net_if_stats", lambda: mock_stats)
    monkeypatch.setattr("psutil.net_io_counters", lambda pernic=True: mock_io)

    selected_ip = get_local_ip()
    assert selected_ip == "192.168.1.200"


def test_get_local_ip_prioritizes_internet_connection(monkeypatch):
    import socket
    from collections import namedtuple

    from desktop.core.network import get_local_ip

    Addr = namedtuple("Addr", ["family", "address"])
    Stats = namedtuple("Stats", ["isup", "speed", "flags"])
    IO = namedtuple("IO", ["bytes_sent", "bytes_recv"])

    mock_addrs = {
        "en0": [Addr(family=socket.AF_INET, address="192.168.1.100")],
        "en1": [Addr(family=socket.AF_INET, address="192.168.1.200")],
    }
    mock_stats = {
        "en0": Stats(isup=True, speed=100, flags="up,broadcast"),
        "en1": Stats(isup=True, speed=1000, flags="up,broadcast"),
    }
    mock_io = {
        "en0": IO(bytes_sent=1000, bytes_recv=1000),  # kevesebb forgalom
        "en1": IO(bytes_sent=99999, bytes_recv=99999),  # nagyobb forgalom
    }

    monkeypatch.setattr("psutil.net_if_addrs", lambda: mock_addrs)
    monkeypatch.setattr("psutil.net_if_stats", lambda: mock_stats)
    monkeypatch.setattr("psutil.net_io_counters", lambda pernic=True: mock_io)

    # Csak az en0-n (192.168.1.100) van internetkapcsolat
    monkeypatch.setattr(
        "desktop.core.network.check_interface_internet",
        lambda ip: ip == "192.168.1.100",
    )

    selected_ip = get_local_ip()
    assert selected_ip == "192.168.1.100"
