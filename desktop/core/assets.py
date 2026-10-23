import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from desktop.core.signals import AppStatus


def get_asset_path(filename: str) -> Path | None:
    """Megkeresi az adott nevű assetet fejlesztői és csomagolt (PyInstaller) környezetben."""
    candidates = []

    # PyInstaller csomagolt környezet
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.extend(
            [
                Path(meipass) / "desktop" / "assets" / filename,
                Path(meipass) / "assets" / filename,
            ]
        )
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        candidates.extend(
            [
                exe.parent / "desktop" / "assets" / filename,
                exe.parent / "assets" / filename,
                exe.parent.parent / "Resources" / "desktop" / "assets" / filename,
                exe.parent.parent / "Resources" / "assets" / filename,
            ]
        )

    # Fejlesztői környezet
    candidates.append(Path(__file__).resolve().parent.parent / "assets" / filename)

    for path in candidates:
        if path.exists():
            return path
    return None


def create_tray_icon(status: AppStatus) -> QIcon:
    """QIcon generálása vagy betöltése az aktuális státusznak megfelelően."""
    specific_icon = get_asset_path(f"icon_{status.value}.png")
    fallback_icon = get_asset_path("icon.png")
    asset_path = specific_icon or fallback_icon

    if asset_path and asset_path.exists():
        return QIcon(str(asset_path))

    # Ha nincs fizikai képfájl, renderelünk egy szép, éles kört QPixmap és QPainter segítségével
    color_map = {
        AppStatus.STARTING: QColor(241, 196, 15),
        AppStatus.RUNNING: QColor(46, 204, 113),
        AppStatus.ERROR: QColor(231, 76, 60),
    }
    color = color_map.get(status, QColor(46, 204, 113))

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(4, 4, 56, 56)
    painter.end()

    return QIcon(pixmap)
