import importlib
import inspect
import pkgutil
from pathlib import Path

from app.modules.network.ddns.base import BaseDDNSProvider


def discover_dns_providers() -> list[type[BaseDDNSProvider]]:
    providers: list[type[BaseDDNSProvider]] = []
    package_dir = Path(__file__).parent / "providers"

    if not package_dir.exists():
        return providers

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        module = importlib.import_module(
            f".providers.{module_info.name}", package=__package__
        )
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseDDNSProvider)
                and obj is not BaseDDNSProvider
                and obj.__module__ == module.__name__
            ):
                providers.append(obj)

    return providers
