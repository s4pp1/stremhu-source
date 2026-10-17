from enum import Enum

from PySide6.QtCore import QObject, Signal


class AppStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class DesktopSignals(QObject):
    """Központi szignálok a háttérszál (FastAPI/Hypercorn) és a fő UI-szál (PySide6) közötti szálbiztos kommunikációhoz."""

    status_changed = Signal(AppStatus)
    error_occurred = Signal(str)
    notification_requested = Signal(
        str, str, str
    )  # title, message, level ("info", "warning", "critical")


app_signals = DesktopSignals()
