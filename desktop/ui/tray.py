import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from desktop.core.assets import create_tray_icon
from desktop.core.signals import AppStatus, DesktopSignals
from desktop.ui.dialogs import _ensure_qapp, pick_directory, show_error, show_info
from server.config import config

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
        self.signals = signals
        self.server_manager = server_manager

        if self.signals is not None:
            self.signals.status_changed.connect(self.on_status_changed)
            self.signals.error_occurred.connect(self.on_error_occurred)
            self.signals.notification_requested.connect(self.show_notification)

    @Slot(AppStatus)
    def on_status_changed(self, status: AppStatus) -> None:
        if status == AppStatus.RUNNING:
            self.set_running()
        elif status == AppStatus.STARTING:
            self.status = AppStatus.STARTING
            self.error_message = None
            self.update_tray()
        elif status == AppStatus.ERROR:
            self.status = AppStatus.ERROR
            self.update_tray()

    @Slot(str)
    def on_error_occurred(self, error: str) -> None:
        self.set_error(error)

    def set_running(self) -> None:
        """Beállítja a futó állapotot és frissíti a menüt és az ikont."""
        self.status = AppStatus.RUNNING
        self.error_message = None
        self.update_tray()

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
            self.icon.setContextMenu(self.build_menu())

    def get_app_url(self) -> str:
        try:
            from server.common.database import db_session
            from server.modules.settings.dependencies import create_settings_service

            with db_session() as db:
                service = create_settings_service(db)
                return service.get_app_url()
        except Exception:
            from desktop.core.network import get_local_ip

            local_ip = get_local_ip()
            host_slug = local_ip.replace(".", "-")
            return f"https://{host_slug}.local-ip.medicmobile.org:{config.port}"

    def open_browser(self) -> None:
        if self.is_running():
            webbrowser.open(self.get_app_url())

    def open_settings_in_browser(self) -> None:
        if self.is_running():
            webbrowser.open(f"{self.get_app_url()}/dashboard/system")

    def show_error_details(self) -> None:
        if self.error_message:
            show_error("Hiba részletei", self.error_message)

    def open_downloads_folder(self) -> None:
        folder = config.downloads_dir
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        elif sys.platform == "win32":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def change_downloads_dir(self) -> None:
        current_dir = config.downloads_dir
        new_dir = pick_directory(
            initial_dir=current_dir,
            title="Válaszd ki a StremHU letöltési mappáját",
        )
        if new_dir:
            from server.common.database import db_session
            from server.modules.settings.dependencies import create_settings_service
            from server.modules.settings.schemas.internal import SystemSettingsUpdate

            with db_session() as db:
                settings_service = create_settings_service(db)
                settings_service.save_system(
                    SystemSettingsUpdate(downloads_dir=new_dir)
                )

            Path(new_dir).mkdir(parents=True, exist_ok=True)
            show_info(
                "Beállítások mentve",
                f"A letöltési mappa sikeresen beállítva:\n{new_dir}",
            )

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

        change_folder_action = menu.addAction("Letöltési mappa módosítása...")
        change_folder_action.triggered.connect(self.change_downloads_dir)

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
        self.icon.setContextMenu(self.build_menu())
        return self.icon
