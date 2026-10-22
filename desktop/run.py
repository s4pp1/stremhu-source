import multiprocessing
import sys

import setproctitle

from desktop.core.runner import ServerProcessManager
from desktop.core.signals import app_signals
from desktop.ui.dialogs import _ensure_qapp
from desktop.ui.tray import TrayController


def start_desktop_app() -> None:
    """Elindítja az asztali alkalmazást: PySide6 QSystemTrayIcon a fő GUI folyamatban,

    és a StremHU Core önálló háttérfolyamatként fut.
    """
    try:
        setproctitle.setproctitle("StremHU Desktop")
    except Exception:
        pass

    app = _ensure_qapp()
    app.setApplicationName("StremHU")
    app.setApplicationDisplayName("StremHU")
    app.setQuitOnLastWindowClosed(False)

    server_manager = ServerProcessManager(signals=app_signals)
    tray_controller = TrayController(signals=app_signals, server_manager=server_manager)
    tray = tray_controller.create_tray()
    tray.show()

    # Elindítjuk a StremHU Core önálló folyamatot
    server_manager.start()

    # A PySide6 eseményhurkot futtatjuk a fő szálon
    exit_code = app.exec()
    server_manager.stop()
    sys.exit(exit_code)


def main() -> None:
    multiprocessing.freeze_support()
    # Ha a csomagolt binárist a --server kapcsolóval indítják, a kiszolgálót futtatjuk
    if "--server" in sys.argv:
        from server.main import run

        run()
        return

    start_desktop_app()


if __name__ == "__main__":
    main()
