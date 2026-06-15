import importlib
import inspect
import pkgutil
from pathlib import Path

from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)


def discover_indexer_definitions() -> list[type[BaseIndexerDefinition]]:
    indexer_definitions: list[type[BaseIndexerDefinition]] = []
    package_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        module = importlib.import_module(f".{module_info.name}", package=__package__)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseIndexerDefinition)
                and obj is not BaseIndexerDefinition
                and obj.__module__ == module.__name__
            ):
                indexer_definitions.append(obj)

    return indexer_definitions
