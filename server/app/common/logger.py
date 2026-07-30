import logging

from rich.logging import RichHandler

from app.config import NodeEnv, config


def setup_logger():
    is_prod = config.node_env == NodeEnv.PROD

    logging.basicConfig(
        level=logging.WARNING if is_prod else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=True)],
        force=True,
    )


logger = logging.getLogger(__name__)
