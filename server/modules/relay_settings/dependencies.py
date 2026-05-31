from fastapi import Depends
from modules.relay.dependencies import get_relay_service
from modules.relay.service import RelayService
from modules.relay_settings.service import RelaySettingsService
from modules.settings.dependencies import get_settings_service
from modules.settings.service import SettingsService


def get_relay_settings_service(
    settings_service: SettingsService = Depends(get_settings_service),
    relay_service: RelayService = Depends(get_relay_service),
) -> RelaySettingsService:
    return RelaySettingsService(settings_service, relay_service)
