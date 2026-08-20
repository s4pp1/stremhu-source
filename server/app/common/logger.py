import logging
import shutil

from rich.console import Console
from rich.logging import RichHandler

from app.config import NodeEnv, config


class IgnoreHypercornDisconnectErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            if (
                exc_type
                and exc_type.__name__ == "LocalProtocolError"
                and "Too little data for declared Content-Length" in str(exc_value)
            ):
                return False
        return True


def setup_logger():
    is_prod = config.node_env == NodeEnv.PROD

    terminal_width = shutil.get_terminal_size(fallback=(120, 50)).columns
    console = Console(width=terminal_width)

    handler = RichHandler(
        rich_tracebacks=True,
        show_path=True,
        console=console,
    )
    handler.addFilter(IgnoreHypercornDisconnectErrorFilter())

    logging.basicConfig(
        level=logging.WARNING if is_prod else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
        force=True,
    )


logger = logging.getLogger(__name__)
