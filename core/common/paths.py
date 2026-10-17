import sys
from importlib.resources import files
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_core_dir() -> Path:
    if is_frozen():
        bundle_dir = getattr(sys, "_MEIPASS", Path(sys.executable).parent)
        return Path(bundle_dir)

    return Path(str(files("core")))
