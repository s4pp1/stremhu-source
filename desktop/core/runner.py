import os
import subprocess
import sys
import time
from pathlib import Path

import platformdirs
from PySide6.QtCore import QObject, QTimer

from desktop.core.api import fetch_system_status
from desktop.core.network import get_local_ip
from desktop.core.signals import AppStatus, DesktopSignals, app_signals


def is_server_port_open(port: int) -> bool:
    """Megvizsgálja, hogy a StremHU Server kiszolgáló elérhető-e a megadott porton REST API-n keresztül."""
    return fetch_system_status(port) is not None


def get_desktop_client_dir() -> Path:
    """Meghatározza a kliens mappa helyét a desktop környezet alapján."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / "client"
            if cand.exists():
                return cand
        exe = Path(sys.executable)
        candidates = [
            exe.parent.parent / "Resources" / "client",
            exe.parent.parent / "Frameworks" / "client",
            exe.parent / "client",
        ]
        for c in candidates:
            if c.exists():
                return c

    root_dir = Path(__file__).resolve().parent.parent.parent
    for candidate in [root_dir / "server" / "client", root_dir / "client" / "dist"]:
        if candidate.exists():
            return candidate
    return root_dir / "server" / "client"


def get_desktop_system_dir() -> Path:
    """Meghatározza az alkalmazás perzisztens adatkönyvtárát az operációs rendszer szerint."""
    return Path(platformdirs.user_data_dir("StremHU", appauthor=False))


def get_desktop_downloads_dir() -> Path:
    """Meghatározza a felhasználó alapértelmezett letöltési mappáját."""
    return Path(platformdirs.user_downloads_dir())


class ServerProcessManager(QObject):
    """A StremHU Server folyamatát felügyelő Sidecar menedzser.

    Működési elve:
    1. Ha a szerver már fut (pl. külön terminálban vagy debuggerben),
       automatikusan rácsatlakozik REST API-n keresztül és felügyeli.
    2. Ha még nem fut, elindítja a háttérfolyamatot (frozen módban a natív binárist,
       dev módban a 'python -m server'-t).
    3. Ha a szerver újraindul (pl. a web UI 'Újraindítás' gombjára nyomva),
       automatikusan újraindítja a child processzt.
    4. Kilépéskor leállítja a saját maga által indított child processzt.
    """

    def __init__(self, signals: DesktopSignals = app_signals) -> None:
        super().__init__()
        self.signals = signals
        self.port: int = 7070
        self.status: AppStatus = AppStatus.STARTING
        self.process: subprocess.Popen[bytes] | None = None
        self.is_external = False
        self._stopping = False
        self._last_start_time = 0.0
        self._rapid_crash_count = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_status)

    def start(self) -> None:
        """Elindítja vagy rácsatlakozik a StremHU Server kiszolgálóra."""
        self._stopping = False

        # 1. Intelligens csatlakozás: ha már fut a szerver, nem indítunk újat
        if is_server_port_open(self.port):
            status = fetch_system_status(self.port)
            if status:
                self.port = status.port
            self.is_external = True
            self.status = AppStatus.RUNNING
            self.signals.status_changed.emit(AppStatus.RUNNING)
            self._timer.start(1000)
            return

        # 2. Sidecar indítása: háttérfolyamat elindítása
        self.is_external = False
        root_dir = Path(__file__).resolve().parent.parent.parent

        env = os.environ.copy()
        existing_pp = env.get("PYTHONPATH", "")
        needed_paths = [str(root_dir), str(root_dir / "server")]
        env["PYTHONPATH"] = ":".join(
            [p for p in needed_paths if p] + ([existing_pp] if existing_pp else [])
        )

        client_path = str(get_desktop_client_dir())
        host_ip = get_local_ip()
        system_dir = get_desktop_system_dir()
        default_downloads_dir = get_desktop_downloads_dir()

        cmd_args = [
            "--client-path",
            client_path,
            "--host-ip",
            host_ip,
            "--system-dir",
            str(system_dir),
            "--default-downloads-dir",
            str(default_downloads_dir),
        ]

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--server"] + cmd_args
        else:
            cmd = [sys.executable, "-m", "server"] + cmd_args

        self._last_start_time = time.time()
        cwd = (
            str(Path(sys.executable).parent)
            if getattr(sys, "frozen", False)
            else str(root_dir)
        )
        self.process = subprocess.Popen(cmd, env=env, cwd=cwd)
        self.status = AppStatus.STARTING
        self.signals.status_changed.emit(AppStatus.STARTING)
        self._timer.start(1000)

    def stop(self) -> None:
        """Leállítja a child folyamatot kulturáltan."""
        self._stopping = True
        self._timer.stop()

        if self.process and not self.is_external:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except (subprocess.TimeoutExpired, Exception):
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        self.status = AppStatus.STARTING
        self.signals.status_changed.emit(AppStatus.STARTING)

    def _check_status(self) -> None:
        """Időzített ellenőrző ciklus: figyeli a portot és a child process állapotát REST API-n."""
        if self._stopping:
            return

        # 1. Ha külső szerverhez csatlakoztunk, csak a portot figyeljük
        if self.is_external:
            if not is_server_port_open(self.port):
                self.is_external = False
                self._timer.stop()
                self.status = AppStatus.STARTING
                self.signals.status_changed.emit(AppStatus.STARTING)
                self.start()
            return

        # 2. Ha saját processzünk fut, figyeljük a státuszát
        if self.process is not None:
            retcode = self.process.poll()
            if retcode is not None:
                # A szerver leállt (pl. web UI újraindítás vagy hiba miatt)
                uptime = time.time() - self._last_start_time
                if uptime < 3.0:
                    self._rapid_crash_count += 1
                else:
                    self._rapid_crash_count = 0

                self.process = None
                self._timer.stop()

                if self._rapid_crash_count >= 3:
                    self.status = AppStatus.ERROR
                    self.signals.error_occurred.emit(
                        f"A StremHU szerver egymás után {self._rapid_crash_count}-szor leállt (kilépési kód: {retcode}). "
                        "Kérlek ellenőrizd a naplófájlokat vagy a portbeállításokat!"
                    )
                    return

                # Újraindítás kísérlet
                self.status = AppStatus.STARTING
                self.signals.status_changed.emit(AppStatus.STARTING)
                self.start()
                return

            # Ha a szerver még STARTING állapotban van, ellenőrizzük, hogy válaszol-e már
            if self.status != AppStatus.RUNNING and is_server_port_open(self.port):
                status = fetch_system_status(self.port)
                if status:
                    self.port = status.port
                self.status = AppStatus.RUNNING
                self.signals.status_changed.emit(AppStatus.RUNNING)
