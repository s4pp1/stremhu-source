import asyncio
import os

from server.common.logger import logger
from server.config import config
from server.modules.roles.models import RoleModel
from server.modules.roles.service import RolesService
from server.modules.settings.service import SettingsService
from server.modules.system.schemas.internal import SystemStatus
from server.modules.users.service import UsersService


class SystemService:
    def __init__(
        self,
        users_service: UsersService,
        settings_service: SettingsService,
        roles_service: RolesService,
    ):
        self._users_service = users_service
        self._settings_service = settings_service
        self._roles_service = roles_service

    def get_roles(self) -> list[RoleModel]:
        return self._roles_service.find_list()

    def status(self) -> SystemStatus:
        has_user = self._users_service.count() > 0
        app_url = self._settings_service.get_app_url()
        system_settings = self._settings_service.get_system()

        return SystemStatus(
            configured=has_user,
            app_url=app_url,
            version=config.version,
            host_ip=config.host_ip,
            port=system_settings.port,
            is_reverse_proxy=config.reverse_proxy_domain is not None,
            is_docker=config.is_docker,
            is_port_overridden=config.is_port_overridden,
        )

    async def restart(self):
        logger.info("Az alkalmazás leáll, hogy a Docker újraindíthassa a konténert...")
        await asyncio.sleep(2)
        try:
            os._exit(1)
        except Exception as e:
            logger.critical("Súlyos hiba történt az automatikus leállítás során: %s", e)
