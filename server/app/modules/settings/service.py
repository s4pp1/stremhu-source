from pydantic import TypeAdapter

from app.config import config
from app.modules.settings.enums import NetworkModeEnum, SettingsKeyEnum
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.schemas.internal import (
    NetworkSettings,
    RelaySettings,
    RelaySettingsUpdate,
    SystemSettings,
    SystemSettingsUpdate,
)


class SettingsService:
    def __init__(
        self,
        settings_repository: SettingsRepository,
    ):
        self._settings_repository = settings_repository

    # System Settings

    def save_system(self, payload: SystemSettingsUpdate) -> SystemSettings:
        system_settings = self.find_system()
        if not system_settings:
            system_settings = SystemSettings()

        data = payload.model_dump(exclude_unset=True)
        updated_data = system_settings.model_copy(update=data).model_dump()

        self._settings_repository.save(SettingsKeyEnum.SYSTEM, updated_data)

        return SystemSettings.model_validate(updated_data)

    def find_system(self) -> SystemSettings | None:
        record = self._settings_repository.find_one(SettingsKeyEnum.SYSTEM.value)
        if not record or not record.value:
            return None
        return SystemSettings.model_validate(record.value)

    def get_system(self) -> SystemSettings:
        system_settings = self.find_system()
        if not system_settings:
            raise ValueError("A rendszerbeállítások nem léteznek.")
        return system_settings

    # Relay Settings

    def save_relay(self, payload: RelaySettingsUpdate) -> RelaySettings:
        relay_settings = self.find_relay()
        if not relay_settings:
            relay_settings = RelaySettings()

        data = payload.model_dump(exclude_unset=True)
        updated_data = relay_settings.model_copy(update=data).model_dump()

        self._settings_repository.save(SettingsKeyEnum.RELAY, updated_data)

        return RelaySettings.model_validate(updated_data)

    def find_relay(self) -> RelaySettings | None:
        record = self._settings_repository.find_one(SettingsKeyEnum.RELAY.value)
        if not record or not record.value:
            return None
        return RelaySettings.model_validate(record.value)

    def get_relay(self) -> RelaySettings:
        relay_settings = self.find_relay()
        if not relay_settings:
            raise ValueError("A Relay beállítások nem léteznek.")
        return relay_settings

    # Network Settings

    def save_network(self, payload: NetworkSettings) -> NetworkSettings:
        self._settings_repository.save(SettingsKeyEnum.NETWORK, payload.model_dump())
        return payload

    def find_network(self) -> NetworkSettings | None:
        record = self._settings_repository.find_one(SettingsKeyEnum.NETWORK.value)
        if not record or not record.value:
            return None
        return TypeAdapter(NetworkSettings).validate_python(record.value)

    def get_network(self) -> NetworkSettings:
        network_settings = self.find_network()
        if not network_settings:
            raise ValueError("Nincs beállítva hálózati elérés")
        return network_settings

    def get_app_url(self) -> str:
        network_settings = self.get_network()
        if network_settings.mode == NetworkModeEnum.MANUAL:
            return f"https://{network_settings.host}"

        return f"https://{network_settings.host}:{config.port}"
