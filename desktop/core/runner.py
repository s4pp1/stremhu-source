import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from desktop.core.signals import AppStatus, DesktopSignals, app_signals
from server.config import config


def is_port_in_use(port: int) -> bool:
    """Megvizsgálja, hogy a megadott port foglalt-e (hallgat rajta folyamat vagy nem köthető le)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return True

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            return False
    except OSError:
        return True


def is_stremhu_server(port: int) -> bool:
    """Megvizsgálja, hogy az adott porton valóban a StremHU Core kiszolgáló fut-e."""
    import json
    import ssl
    import urllib.request

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://127.0.0.1:{port}/api/system/status"
    req = urllib.request.Request(url, headers={"User-Agent": "StremHU-Desktop"})
    try:
        with urllib.request.urlopen(req, timeout=0.5, context=ctx) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return isinstance(data, dict) and "configured" in data
    except Exception:
        return False
    return False


def is_server_port_open(port: int) -> bool:
    """Megvizsgálja, hogy a StremHU Core kiszolgáló elérhető-e a megadott porton."""
    return is_stremhu_server(port)


def find_available_port(start_port: int = 7071, max_attempts: int = 100) -> int:
    """Megkeresi az első szabad portot a kezdő porttól felfelé haladva."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    raise RuntimeError(
        f"Nem található szabad port a(z) {start_port} és {start_port + max_attempts} közötti tartományban."
    )


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


class ServerProcessManager(QObject):
    """A StremHU Core folyamatát felügyelő Smart Sidecar menedzser.

    Működési elve (Supervisor / Smart Attach):
    1. Ha a szerver már fut (pl. külön terminálban vagy debuggerben),
       automatikusan rácsatlakozik és felügyeli a portot.
    2. Ha még nem fut, ellenőrzi, hogy a beállított port szabad-e. Ha idegen
       alkalmazás foglalja, automatikusan szabad portot választ és ment az adatbázisba.
    3. Elindítja a háttérfolyamatot (frozen módban a natív binárist,
       dev módban a 'python -m server'-t). A szerver logjai közvetlenül a konzolra íródnak.
    4. Ha a szerver újraindul (pl. a web UI 'Újraindítás' gombjára nyomva),
       automatikusan újraindítja a child processzt anélkül, hogy a desktop app bezáródna.
    5. Kilépéskor kulturáltan leállítja a saját maga által indított child processzt.
    """

    def __init__(self, signals: DesktopSignals = app_signals) -> None:
        super().__init__()
        self.signals = signals
        self.port: int = 7070
        self.process: subprocess.Popen[bytes] | None = None
        self.is_external = False
        self._stopping = False
        self._last_start_time = 0.0
        self._rapid_crash_count = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_status)

    def start(self) -> None:
        """Elindítja vagy rácsatlakozik a StremHU Core kiszolgálóra."""
        self._stopping = False

        # Port inicializálása és szinkronizálása az adatbázisból
        self.port = 7070
        try:
            from server.boot.settings import ensure_default_settings
            from server.boot.setup import run_migrations, setup_system_dir
            from server.common.database import db_session
            from server.modules.settings.dependencies import create_settings_service

            setup_system_dir()
            run_migrations()
            ensure_default_settings()
            with db_session() as db:
                service = create_settings_service(db)
                self.port = service.get_system().port
        except Exception:
            self.port = config.port or 7070

        # 1. Intelligens csatlakozás: ha már fut a szerver, nem indítunk újat
        if is_server_port_open(self.port):
            self.is_external = True
            self.signals.status_changed.emit(AppStatus.RUNNING)
            self._timer.start(1000)
            return

        # 2. Ütközésvizsgálat: ha a port foglalt egy másik alkalmazás által, szabad portot választunk
        if not config.is_port_overridden and is_port_in_use(self.port):
            try:
                new_port = find_available_port(self.port + 1)
                from server.common.database import db_session
                from server.modules.settings.dependencies import create_settings_service
                from server.modules.settings.schemas.internal import (
                    SystemSettingsUpdate,
                )

                with db_session() as db:
                    service = create_settings_service(db)
                    service.save_system(SystemSettingsUpdate(port=new_port))
                self.port = new_port
                config.port = new_port
            except Exception:
                pass

        # 3. Sidecar indítása: háttérfolyamat elindítása
        self.is_external = False
        root_dir = Path(__file__).resolve().parent.parent.parent

        env = os.environ.copy()
        existing_pp = env.get("PYTHONPATH", "")
        needed_paths = [str(root_dir), str(root_dir / "server")]
        env["PYTHONPATH"] = ":".join(
            [p for p in needed_paths if p] + ([existing_pp] if existing_pp else [])
        )

        import platformdirs

        from desktop.core.network import get_local_ip

        client_path = str(get_desktop_client_dir())
        host_ip = get_local_ip()
        system_dir = Path(platformdirs.user_data_dir("stremhu", "stremhu"))

        cmd_args = [
            "--client-path",
            client_path,
            "--host-ip",
            host_ip,
            "--system-dir",
            str(system_dir),
            "--port",
            str(self.port),
        ]

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--server"] + cmd_args
        else:
            cmd = [sys.executable, "-m", "server"] + cmd_args

        self._last_start_time = time.time()
        # stdout és stderr öröklődik a konzolra, így látszanak az élő szerver logok
        self.process = subprocess.Popen(cmd, env=env, cwd=str(root_dir))

        self.signals.status_changed.emit(AppStatus.RUNNING)
        self._timer.start(1000)

    def _check_status(self) -> None:
        """Rendszeresen ellenőrzi a szerver állapotát."""
        if self._stopping:
            return

        # Külső szerver felügyelete (pl. másik terminálban / debuggerben indítva)
        if self.is_external:
            if is_server_port_open(self.port):
                self.signals.status_changed.emit(AppStatus.RUNNING)
            else:
                self.signals.status_changed.emit(AppStatus.STARTING)
            return

        # Saját child processz felügyelete
        if self.process is None:
            return

        poll_code = self.process.poll()
        if poll_code is not None:
            uptime = time.time() - self._last_start_time
            if uptime < 2.0:
                self._rapid_crash_count += 1
            else:
                self._rapid_crash_count = 0

            # Ha egymás után többször azonnal leáll, kritikus hibát jelzünk
            if self._rapid_crash_count >= 3:
                self._timer.stop()
                self.signals.status_changed.emit(AppStatus.ERROR)
                self.signals.error_occurred.emit(
                    f"A StremHU Core folyamat nem tudott elindulni (hibakód: {poll_code})."
                )
                return

            # Újraindítás (pl. webes felületről történt restart után)
            self.signals.status_changed.emit(AppStatus.STARTING)
            self.start()

    def stop(self) -> None:
        """Kulturáltan leállítja a folyamatfelügyeletet és a saját indítású child processzt."""
        self._stopping = True
        self._timer.stop()

        # Csak a saját indítású folyamatot lőjük le; a külsőleg indított szervert meghagyjuk
        if (
            not self.is_external
            and self.process is not None
            and self.process.poll() is None
        ):
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.is_external = False
