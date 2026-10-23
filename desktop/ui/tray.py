import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from desktop.core.api import fetch_system_status
from desktop.core.assets import create_tray_icon
from desktop.core.network import get_local_ip
from desktop.core.runner import get_desktop_downloads_dir
from desktop.core.signals import AppStatus, DesktopSignals
from desktop.ui.dialogs import _ensure_qapp, show_error

if TYPE_CHECKING:
    from desktop.core.runner import ServerProcessManager


class TrayController(QObject):
    """A StremHU tálcaikonját és környezeti menüjét kezelő vezérlő."""

    def __init__(
        self,
        signals: DesktopSignals | None = None,
        server_manager: "ServerProcessManager | None" = None,
    ) -> None:
        super().__init__()
        _ensure_qapp()

        self.status: AppStatus = AppStatus.STARTING
        self.error_message: str | None = None
        self.icon: QSystemTrayIcon | None = None
        self._context_menu: QMenu | None = None
        self._cached_app_url: str | None = None
        self._cached_downloads_dir: Path | None = None
        self.signals = signals
        self.server_manager = server_manager

        if self.signals is not None:
            self.signals.status_changed.connect(self.on_status_changed)
            self.signals.error_occurred.connect(self.on_error_occurred)
            self.signals.notification_requested.connect(self.show_notification)

    @Slot(AppStatus)
    def on_status_changed(self, status: AppStatus) -> None:
        if status == self.status:
            return

        self.status = status
        if status == AppStatus.RUNNING:
            self.set_running()
        elif status == AppStatus.STARTING:
            self.error_message = None
            self._cached_app_url = None
            self._cached_downloads_dir = None
            self.update_tray()
        elif status == AppStatus.ERROR:
            self.update_tray()

    @Slot(str)
    def on_error_occurred(self, error: str) -> None:
        self.set_error(error)

    def set_running(self) -> None:
        """Beállítja a futó állapotot és frissíti a menüt és az ikont."""
        self.status = AppStatus.RUNNING
        self.error_message = None
        self._refresh_cached_data()
        self.update_tray()

    def _refresh_cached_data(self) -> None:
        port = self.server_manager.port if self.server_manager else 7070
        status = fetch_system_status(port)
        if status:
            if status.app_url:
                self._cached_app_url = status.app_url
            if status.downloads_dir:
                self._cached_downloads_dir = status.downloads_dir

    def set_error(self, error: str) -> None:
        """Beállítja a hiba állapotot, frissíti az ikont és felugró hibaablakot jelenít meg."""
        self.status = AppStatus.ERROR
        self.error_message = error
        self.update_tray()
        show_error(
            "StremHU Indítási Hiba",
            f"Nem sikerült a StremHU elindítása:\n\n{error}",
        )

    def is_running(self) -> bool:
        return self.status == AppStatus.RUNNING

    def update_tray(self) -> None:
        """Frissíti a tálcaikont és a menüt, ha a tray már inicializálva van."""
        if self.icon is not None:
            self.icon.setIcon(create_tray_icon(self.status))
            self._context_menu = self.build_menu()
            self.icon.setContextMenu(self._context_menu)

    def get_app_url(self) -> str:
        """Lekéri az alkalmazás elérési URL-jét a REST API-n keresztül vagy cache-ből."""
        if self._cached_app_url:
            return self._cached_app_url

        port = self.server_manager.port if self.server_manager else 7070
        status = fetch_system_status(port)
        if status and status.app_url:
            self._cached_app_url = status.app_url
            return status.app_url

        local_ip = get_local_ip()
        host_slug = local_ip.replace(".", "-")
        return f"https://{host_slug}.local-ip.medicmobile.org:{port}"

    def open_browser(self) -> None:
        if self.is_running():
            webbrowser.open(self.get_app_url())

    def open_settings_in_browser(self) -> None:
        if self.is_running():
            webbrowser.open(f"{self.get_app_url()}/dashboard/system")

    def show_error_details(self) -> None:
        if self.error_message:
            show_error("Hiba részletei", self.error_message)

    def _get_downloads_dir(self) -> Path:
        """Lekéri a beállított letöltési mappát a REST API-n keresztül vagy cache-ből."""
        if self._cached_downloads_dir:
            return self._cached_downloads_dir

        port = self.server_manager.port if self.server_manager else 7070
        status = fetch_system_status(port)
        if status and status.downloads_dir:
            self._cached_downloads_dir = status.downloads_dir
            return status.downloads_dir
        return get_desktop_downloads_dir()

    def open_downloads_folder(self) -> None:
        folder = self._get_downloads_dir()
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        elif sys.platform == "win32":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def quit_app(self) -> None:
        """Alkalmazás leállítása és tálcaikon elrejtése."""
        if self.icon is not None:
            self.icon.hide()
        if self.server_manager is not None:
            self.server_manager.stop()
        app = QApplication.instance()
        if app is not None:
            app.quit()
        sys.exit(0)

    def build_menu(self) -> QMenu:
        """Dinamikusan felépíti a Qt menüt az aktuális állapot (STARTING, RUNNING, ERROR) alapján."""
        menu = QMenu()

        if self.status == AppStatus.STARTING:
            status_item = menu.addAction("⏳ StremHU indítása (migrációk)...")
            status_item.setEnabled(False)
            menu.addSeparator()
            quit_action = menu.addAction("Kilépés")
            quit_action.triggered.connect(self.quit_app)
            return menu

        if self.status == AppStatus.ERROR:
            status_item = menu.addAction("🔴 Hiba az indításkor!")
            status_item.setEnabled(False)
            menu.addSeparator()
            details_action = menu.addAction("Hiba részletei...")
            details_action.triggered.connect(self.show_error_details)
            menu.addSeparator()
            quit_action = menu.addAction("Kilépés")
            quit_action.triggered.connect(self.quit_app)
            return menu

        # AppStatus.RUNNING
        status_item = menu.addAction("🟢 StremHU fut")
        status_item.setEnabled(False)
        menu.addSeparator()

        open_browser_action = menu.addAction("Megnyitás Böngészőben")
        open_browser_action.triggered.connect(self.open_browser)

        settings_action = menu.addAction("Beállítások a Böngészőben")
        settings_action.triggered.connect(self.open_settings_in_browser)

        menu.addSeparator()

        open_folder_action = menu.addAction("Letöltési mappa megnyitása")
        open_folder_action.triggered.connect(self.open_downloads_folder)

        menu.addSeparator()

        quit_action = menu.addAction("Kilépés")
        quit_action.triggered.connect(self.quit_app)

        return menu

    def show_notification(self, title: str, message: str, level: str = "info") -> None:
        """Natív operációs rendszer értesítés megjelenítése a tálcaikonon keresztül."""
        if self.icon is not None:
            icon_type = QSystemTrayIcon.MessageIcon.Information
            if level == "warning":
                icon_type = QSystemTrayIcon.MessageIcon.Warning
            elif level == "critical":
                icon_type = QSystemTrayIcon.MessageIcon.Critical
            self.icon.showMessage(title, message, icon_type, 4000)

    def create_tray(self) -> QSystemTrayIcon:
        """Létrehozza a QSystemTrayIcon példányt és beállítja az ikont, menüt és tooltipet."""
        self.icon = QSystemTrayIcon(create_tray_icon(self.status))
        self.icon.setToolTip("StremHU")
        self._context_menu = self.build_menu()
        self.icon.setContextMenu(self._context_menu)
        return self.icon
