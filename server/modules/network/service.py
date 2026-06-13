import asyncio
import time

import httpx
from common.logger import logger
from config import config
from cryptography import x509
from modules.network.ddns.schemas.internal import DDNSIpUpdate
from modules.network.ddns.service import DDNSService
from modules.network.schemas.internal import NetworkSetup
from modules.network.ssl.schemas import AcmeCertificateGenerate, SelfSignedCertificate
from modules.network.ssl.service import SslService
from modules.settings.schemas.internal import (
    NetworkAutoSettings,
    NetworkLocalSettings,
    NetworkManualSettings,
    NetworkModeEnum,
    NetworkSettings,
)
from modules.settings.service import SettingsService
from modules.system.service import SystemService


class NetworkService:
    def __init__(
        self,
        settings_service: SettingsService,
        ssl_service: SslService,
        ddns_service: DDNSService,
        system_service: SystemService,
    ):
        self._settings_service = settings_service
        self._ssl_service = ssl_service
        self._ddns_service = ddns_service
        self._system_service = system_service
        self._in_progress = False

    async def setup_local(self) -> tuple[NetworkSettings, SelfSignedCertificate]:
        certs = await self._ssl_service.get_local_ip_certificate(config.host_ip)

        cert = x509.load_pem_x509_certificate(certs.fullchain.encode("utf-8"))
        if cert.issuer == cert.subject:
            host = config.host_ip
            self_signed = True
        else:
            host = config.host_ip.replace(".", "-") + ".local-ip.medicmobile.org"
            self_signed = False

        local_settings = NetworkLocalSettings(
            mode=NetworkModeEnum.LOCAL,
            host=host,
            self_signed=self_signed,
            ip=config.host_ip,
            fullchain=certs.fullchain,
            privkey=certs.privkey,
            expires_at=certs.expires_at,
        )

        network_settings = await asyncio.to_thread(
            self._settings_service.save_network,
            local_settings,
        )

        return network_settings, certs

    async def check_connectivity(
        self,
        host: str,
    ) -> bool:
        """Ellenőrzi, hogy a szerver elérhető-e kívülről a megadott domain-en."""

        url = f"https://{host}:{config.port}/api/health"

        logger.info("🔍 Hálózati elérhetőség ellenőrzése: %s", url)

        # A tanúsítvány még lehet self-signed vagy hiányozhat, így kikapcsoljuk az SSL ellenőrzést
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            for attempt in range(6):
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info("✅ Hálózati kapcsolat sikeresen ellenőrizve!")
                        return True
                except Exception as e:
                    logger.debug(
                        "Csatlakozási kísérlet %s sikertelen: %s", attempt + 1, e
                    )
                await asyncio.sleep(10)

        return False

    async def setup(self, payload: NetworkSetup) -> NetworkSettings:
        if self._in_progress:
            raise ValueError("Hálózati elérés beállítása már folyamatban van!")

        try:
            self._in_progress = True

            current_network_settings = await asyncio.to_thread(
                self._settings_service.get_network
            )

            if payload.mode == NetworkModeEnum.LOCAL:
                network_settings, certs = await self.setup_local()

                asyncio.create_task(self._system_service.restart())

                return network_settings

            if payload.mode == NetworkModeEnum.MANUAL:
                manual_network_settings = NetworkManualSettings(
                    mode=NetworkModeEnum.MANUAL,
                    host=payload.host,
                )

                network_settings = await asyncio.to_thread(
                    self._settings_service.save_network,
                    manual_network_settings,
                )

                asyncio.create_task(self._system_service.restart())

                return network_settings

            # Automatikus beállítás (DDNS + SSL)
            logger.info(
                "⚙️ Automatikus hálózati elérés beállítása (Host: %s, DNS: %s)...",
                payload.host,
                payload.provider,
            )

            # 1. DNS IP szinkronizáció
            ip = await self._ddns_service.get_current_ip(payload.connection)
            await self._ddns_service.update(
                provider_id=payload.provider,
                payload=DDNSIpUpdate(
                    provider_token=payload.token,
                    host=payload.host,
                    ip=ip,
                ),
            )

            # 3. Kapcsolat ellenőrzése fallback védelemmel
            is_connected = await self.check_connectivity(
                host=payload.host,
            )
            if not is_connected:
                # Rollback: ha nem érhető el, állítsuk vissza a DNS-t a korábbi beállításra
                logger.warning("🚨 Kapcsolat ellenőrzés sikertelen! Visszagörgetés...")
                if (
                    current_network_settings
                    and current_network_settings.mode == NetworkModeEnum.AUTO
                ):
                    await self._ddns_service.update(
                        provider_id=current_network_settings.provider,
                        payload=DDNSIpUpdate(
                            provider_token=current_network_settings.token,
                            host=current_network_settings.host,
                            ip=current_network_settings.ip,
                        ),
                    )

                raise ValueError(
                    "A szerver nem érhető el a megadott domainen keresztül! "
                    "A DNS rekordokat visszaállítottuk. Ellenőrizd a router port forward beállításait (TCP 4300 port)!"
                )

            # 4. SSL tanúsítvány igénylése
            account_key_pem = None
            if (
                current_network_settings
                and current_network_settings.mode == NetworkModeEnum.AUTO
            ):
                account_key_pem = current_network_settings.account_key

            certs = await self._ssl_service.generate_acme_certificate(
                AcmeCertificateGenerate(
                    ddns_provider_id=payload.provider,
                    ddns_provider_token=payload.token,
                    host=payload.host,
                    email=payload.email,
                    account_key_pem=account_key_pem,
                )
            )

            auto_network = NetworkAutoSettings(
                mode=NetworkModeEnum.AUTO,
                host=payload.host,
                token=payload.token,
                email=payload.email,
                connection=payload.connection,
                provider=payload.provider,
                ip=ip,
                last_ip_sync_at=int(time.time()),
                fullchain=certs.fullchain,
                privkey=certs.privkey,
                expires_at=certs.expires_at,
                account_key=certs.account_key,
            )
            network_settings = self._settings_service.save_network(auto_network)

            asyncio.create_task(self._system_service.restart())

            return network_settings

        finally:
            self._in_progress = False

    async def sync_ip(self):
        try:
            network_settings = await asyncio.to_thread(
                self._settings_service.get_network
            )

            if network_settings.mode != NetworkModeEnum.AUTO:
                return

            # 1. IP ellenőrzés és frissítés
            current_ip = await self._ddns_service.get_current_ip(
                network_settings.connection
            )

            one_day_seconds = 24 * 60 * 60
            should_sync = (
                network_settings.ip != current_ip
                or (int(time.time()) - network_settings.last_ip_sync_at)
                > one_day_seconds
            )

            if should_sync:
                await self._ddns_service.update(
                    provider_id=network_settings.provider,
                    payload=DDNSIpUpdate(
                        provider_token=network_settings.token,
                        host=network_settings.host,
                        ip=current_ip,
                    ),
                )

                network_settings.ip = current_ip
                network_settings.last_ip_sync_at = int(time.time())

                await asyncio.to_thread(
                    self._settings_service.save_network,
                    network_settings,
                )

        except Exception as e:
            logger.error("🚨 Sikertelen IP / SSL szinkronizáció háttérfeladat: %s", e)

    async def check_ssl_certificate(self):
        network_settings = await asyncio.to_thread(self._settings_service.get_network)

        if network_settings.mode == NetworkModeEnum.MANUAL:
            return

        ssl_renewed = False

        if network_settings.mode == NetworkModeEnum.LOCAL:
            two_days_in_seconds = 2 * 24 * 60 * 60
            time_left = network_settings.expires_at - int(time.time())

            if time_left < two_days_in_seconds:
                ssl_renewed = True

        if network_settings.mode == NetworkModeEnum.AUTO:
            thirty_days_in_seconds = 30 * 24 * 60 * 60
            time_left = network_settings.expires_at - int(time.time())

            if time_left < thirty_days_in_seconds:
                try:
                    certs = await self._ssl_service.generate_acme_certificate(
                        AcmeCertificateGenerate(
                            ddns_provider_id=network_settings.provider,
                            ddns_provider_token=network_settings.token,
                            host=network_settings.host,
                            email=network_settings.email,
                            account_key_pem=network_settings.account_key,
                        )
                    )

                    network_settings.fullchain = certs.fullchain
                    network_settings.privkey = certs.privkey
                    network_settings.expires_at = certs.expires_at
                    network_settings.account_key = certs.account_key

                    await asyncio.to_thread(
                        self._settings_service.save_network,
                        network_settings,
                    )

                    ssl_renewed = True
                except Exception:
                    logger.exception(
                        "🚨 Sikertelen Let's Encrypt SSL megújítás a háttérben"
                    )

        if ssl_renewed:
            logger.info("🔄 SSL megújítás sikeres, újraindítás...")
            asyncio.create_task(self._system_service.restart())
