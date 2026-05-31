import asyncio
import logging
import time

import httpx
from config import config
from modules.network.ddns.schemas import DDNSIpUpdate
from modules.network.ddns.service import DDNSService
from modules.network.schemas import NetworkSetup
from modules.network.ssl.schemas import AcmeCertificateGenerate, SelfSignedCertificate
from modules.network.ssl.service import SslService
from modules.settings.schemas import (
    NetworkAutoSettings,
    NetworkLocalSettings,
    NetworkManualSettings,
    NetworkModeEnum,
    NetworkSettings,
)
from modules.settings.service import SettingsService
from modules.system.service import SystemService

logger = logging.getLogger(__name__)


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

    async def initialize_defaults(self):
        """Inicializálja a hálózati beállításokat, ha még nem léteznek."""
        try:
            network_settings = self._settings_service.get_network()

            if not network_settings:
                logger.info(
                    "⚙️ Hálózati elérés inicializálása (Alapértelmezett: Local)..."
                )
                self.setup_local()
        except Exception as e:
            logger.error(
                "Hiba történt a hálózati alapbeállítások betöltése közben: %s", e
            )

    def setup_local(self) -> tuple[NetworkSettings, SelfSignedCertificate]:
        certs = self._ssl_service.generate_self_signed_certificate(config.host_ip)

        local_settings = NetworkLocalSettings(
            mode=NetworkModeEnum.LOCAL,
            host=config.host_ip,
            ip=config.host_ip,
            fullchain=certs.fullchain,
            privkey=certs.privkey,
            expires_at=certs.expires_at,
        )

        network_settings = self._settings_service.save_network(local_settings)

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

    async def setup(self, payload: NetworkSetup) -> None:
        if self._in_progress:
            raise ValueError("Hálózati elérés beállítása már folyamatban van!")

        try:
            self._in_progress = True

            current_network = self._settings_service.get_network_or_raise()

            if payload.mode == NetworkModeEnum.MANUAL:
                manual_network_settings = NetworkManualSettings(
                    mode=NetworkModeEnum.MANUAL,
                    host=payload.host,
                    reverse_proxy=payload.reverse_proxy,
                )

                self._settings_service.save_network(manual_network_settings)

                asyncio.create_task(self._system_service.restart())
                return

            if payload.mode == NetworkModeEnum.AUTO:
                # Automatikus beállítás (DDNS + SSL)
                logger.info(
                    "⚙️ Automatikus hálózati elérés beállítása (Host: %s, DNS: %s)...",
                    payload.host,
                    payload.provider,
                )

                # 1. DNS hitelesítés
                await self._ddns_service.validate(
                    provider_id=payload.provider,
                    host=payload.host,
                    token=payload.token,
                )

                # 2. DNS IP szinkronizáció
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
                    logger.warning(
                        "🚨 Kapcsolat ellenőrzés sikertelen! Visszagörgetés..."
                    )
                    if current_network and current_network.mode == NetworkModeEnum.AUTO:
                        try:
                            await self._ddns_service.update(
                                provider_id=current_network.provider,
                                payload=DDNSIpUpdate(
                                    provider_token=current_network.token,
                                    host=current_network.host,
                                    ip=current_network.ip,
                                ),
                            )
                        except Exception as e:
                            logger.error("Nem sikerült a DNS visszaállítása: %s", e)

                    raise ValueError(
                        "A szerver nem érhető el a megadott domainen keresztül! "
                        "A DNS rekordokat visszaállítottuk. Ellenőrizd a router port forward beállításait (TCP 4300 port)!"
                    )

                # 4. SSL tanúsítvány igénylése
                account_key_pem = None
                if current_network and current_network.mode == NetworkModeEnum.AUTO:
                    account_key_pem = current_network.account_key

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
                    fullchain=certs.fullchain,
                    privkey=certs.privkey,
                    expires_at=certs.expires_at,
                    account_key=certs.account_key,
                )
                self._settings_service.save_network(auto_network)

                # Ütemezzük az újraindítást
                asyncio.create_task(self._system_service.restart())

        finally:
            self._in_progress = False

    async def sync_ip(self):
        """Cron feladat: Ellenőrzi és szinkronizálja az IP cím változásokat és az SSL lejáratot."""
        try:
            network_settings = self._settings_service.get_network_or_raise()

            if network_settings.mode != NetworkModeEnum.AUTO:
                return

            # 1. IP ellenőrzés és frissítés
            current_ip = await self._ddns_service.get_current_ip(
                network_settings.connection
            )

            if network_settings.ip != current_ip:
                logger.info(
                    "🔄 Hálózati IP változás észlelve (%s -> %s). DNS rekordok frissítése...",
                    network_settings.ip,
                    current_ip,
                )

                await self._ddns_service.update(
                    provider_id=network_settings.provider,
                    payload=DDNSIpUpdate(
                        provider_token=network_settings.token,
                        host=network_settings.host,
                        ip=current_ip,
                    ),
                )

                network_settings.ip = current_ip

            # 2. SSL tanúsítvány lejárati ellenőrzés (30 nap = 2592000 másodperc)
            ssl_renewed = False

            thirty_days_in_seconds = 30 * 24 * 60 * 60
            time_left = network_settings.expires_at - int(time.time())
            if time_left < thirty_days_in_seconds:
                logger.warning(
                    "⚠️ Let's Encrypt SSL tanúsítvány hamarosan lejár (%d nap van hátra). "
                    "Automatikus megújítás folyamatban...",
                    max(0, time_left // (24 * 60 * 60)),
                )
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

                    ssl_renewed = True
                except Exception as renewal_err:
                    logger.error(
                        "🚨 Sikertelen Let's Encrypt SSL megújítás a háttérben: %s",
                        renewal_err,
                    )

            self._settings_service.save_network(network_settings)

            if ssl_renewed:
                logger.info("🔄 SSL megújítás sikeres, újraindítás ütemezése...")
                asyncio.create_task(self._system_service.restart())

        except Exception as e:
            logger.error("🚨 Sikertelen IP / SSL szinkronizáció háttérfeladat: %s", e)
