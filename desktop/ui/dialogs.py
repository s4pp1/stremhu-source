import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv if sys.argv else ["stremhu"])


def pick_directory(
    initial_dir: str | Path | None = None,
    title: str = "Válaszd ki a letöltési mappát",
    parent: QWidget | None = None,
) -> str | None:
    """Natív mappaválasztó párbeszédablakot nyit meg."""
    _ensure_qapp()
    selected = QFileDialog.getExistingDirectory(
        parent,
        title,
        str(initial_dir) if initial_dir else "",
        QFileDialog.Option.ShowDirsOnly,
    )
    return selected if selected else None


def show_info(title: str, message: str, parent: QWidget | None = None) -> None:
    """Natív információs üzenetablak."""
    _ensure_qapp()
    QMessageBox.information(parent, title, message)


def show_error(title: str, message: str, parent: QWidget | None = None) -> None:
    """Natív hibaüzenet ablak."""
    _ensure_qapp()
    QMessageBox.critical(parent, title, message)
