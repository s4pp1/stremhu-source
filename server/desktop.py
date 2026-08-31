import os
import sys
import threading
import webbrowser

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item

# Biztosítjuk, hogy az importok működjenek (PyInstaller környezetben is)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fontos: Kézzel importáljuk az összes modellt, hogy a SQLAlchemy registry-be bekerüljenek,
# mielőtt a kapcsolatokat (relationship) megpróbálja feloldani a PyInstaller futtatás során!
# Különben az automatikus kódformázók (pl. ruff, black) törölnék a "nem használt" importokat.
_models = [
    __import__("app.modules.settings.models"),
    __import__("app.modules.indexer_definitions.models"),
    __import__("app.modules.preferences.models"),
    __import__("app.modules.torrents.models"),
    __import__("app.modules.indexer_accounts.models"),
    __import__("app.modules.pairings.models"),
    __import__("app.modules.media_attributes.models"),
    __import__("app.modules.torrent_files.models"),
    __import__("app.modules.roles.models"),
    __import__("app.modules.attributes.models"),
    __import__("app.modules.attribute_exclusions.models"),
    __import__("app.modules.users.models"),
    __import__("app.modules.system_preference_definitions.models"),
    __import__("app.modules.preference_definitions.models"),
    __import__("app.modules.playback_histories.models"),
    __import__("app.modules.user_preference_definitions.models"),
]

from app.config import config
from app.run import run_migrations, setup_directories, start_server


def run_server(use_reloader=False):
    setup_directories()
    run_migrations()
    try:
        start_server(use_reloader=use_reloader)
    except Exception as e:
        print(f"Szerver futási hiba: {e}")


def open_browser():
    from app.boot.network import get_local_ip

    local_ip = get_local_ip()
    host_slug = local_ip.replace(".", "-")
    url = f"https://{host_slug}.local-ip.medicmobile.org:{config.port}"
    webbrowser.open(url)


def quit_app(icon=None):
    if icon:
        icon.stop()
    os._exit(0)


def open_settings_from_tray():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.call("wm", "attributes", ".", "-topmost", True)

    current_dir = config.downloads_dir
    new_dir = filedialog.askdirectory(
        parent=root, initialdir=current_dir, title="Válaszd ki a letöltési mappát"
    )
    if new_dir:
        from app.config import get_env_paths

        env_file = get_env_paths()[0]
        lines = []
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                lines = f.readlines()

        with open(env_file, "w", encoding="utf-8") as f:
            found = False
            for line in lines:
                if line.startswith("DOWNLOADS_DIR_OVERRIDE="):
                    f.write(f"DOWNLOADS_DIR_OVERRIDE={new_dir}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"DOWNLOADS_DIR_OVERRIDE={new_dir}\n")

        messagebox.showinfo(
            "Beállítások",
            "A letöltési mappa sikeresen beállítva.\nAz új beállítások a következő induláskor lépnek érvénybe.",
            parent=root,
        )
    root.destroy()


def create_image():
    # Létrehoz egy egyszerű zöld kört ikonként
    image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, 60, 60], fill=(46, 204, 113))
    return image


def create_tray():
    icon = pystray.Icon("StremHU")
    icon.menu = pystray.Menu(
        item("StremHU fut...", lambda: None, enabled=False),
        item("Megnyitás Böngészőben", lambda: open_browser()),
        item("Beállítások (Letöltési mappa)...", lambda: open_settings_from_tray()),
        pystray.Menu.SEPARATOR,
        item("Kiszolgáló Leállítása", lambda: quit_app(icon)),
    )
    icon.icon = create_image()
    icon.title = "StremHU"
    icon.run()


import multiprocessing


def patch_signals_for_thread():
    """Megakadályozza, hogy a háttérszálban futó Hypercorn megpróbálja beállítani a signal handlereket, ami összeomlást okozna."""
    import asyncio
    import signal

    def mock_signal(signum, handler):
        pass

    signal.signal = mock_signal

    if hasattr(asyncio, "unix_events"):
        import asyncio.unix_events

        if hasattr(asyncio.unix_events, "_UnixSelectorEventLoop"):
            asyncio.unix_events._UnixSelectorEventLoop.add_signal_handler = (
                lambda *args, **kwargs: None
            )


def run_server_in_thread():
    patch_signals_for_thread()

    # Ha a PyInstaller csomagolta (frozen), ne használjunk reloadert (néma, background mód)
    # Ha fejlesztői módban (pl. VS Code) indítjuk, használhatunk reloadert.
    is_frozen = getattr(sys, "frozen", False)
    use_reloader = not is_frozen

    run_server(use_reloader=use_reloader)


if __name__ == "__main__":
    multiprocessing.freeze_support()

    if "--run-server" in sys.argv:
        # Backward compatibility if ever launched with --run-server
        is_frozen = getattr(sys, "frozen", False)
        run_server(use_reloader=not is_frozen)
    else:
        # A szervert egy háttérszálon indítjuk a signal handlerek mockolásával
        # Így minden egyetlen processzben marad, és nem ugrik fel extra ikon a Dock-ban
        server_thread = threading.Thread(target=run_server_in_thread, daemon=True)
        server_thread.start()

        create_tray()
