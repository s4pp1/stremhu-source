import asyncio
import datetime
import ipaddress
from collections.abc import Awaitable, Callable
from typing import cast

import dns.asyncresolver
import dns.exception
import dns.resolver
import httpx
from acme import challenges, client, errors as acme_errors, messages
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from josepy import jwk

from app.common.log_safety import network_error_fields
from app.common.logger import logger
from app.config import config
from app.modules.network.ddns.schemas.internal import DDNSTxtUpdate
from app.modules.network.ddns.service import DDNSService
from app.modules.network.ssl.schemas import (
    AcmeCertificate,
    AcmeCertificateGenerate,
    SelfSignedCertificate,
)


async def resolve_txt_async(host: str) -> list[str]:
    resolver = dns.asyncresolver.Resolver(configure=False)
    # Nyilvános DNS szerverek lekérdezése (elkerülve a helyi cache-elést)
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]

    answers = await resolver.resolve(host, "TXT")
    return [segment.decode("utf-8") for record in answers for segment in record.strings]


async def wait_for_dns_propagation(
    host: str,
    expected_txt: str,
    timeout: float = 300,
    delay: float = 10,
    *,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> bool:
    now = clock or asyncio.get_running_loop().time
    pause = sleep or asyncio.sleep
    deadline = now() + timeout
    txt_domain = f"_acme-challenge.{host}"
    while (remaining := deadline - now()) > 0:
        try:
            async with asyncio.timeout(remaining):
                answers = await resolve_txt_async(txt_domain)
            if now() >= deadline:
                break
            if expected_txt in answers:
                logger.info("✅ A DNS TXT rekord sikeresen propagált!")
                return True
        except dns.exception.DNSException:
            pass
        except TimeoutError:
            break
        remaining = deadline - now()
        if remaining <= 0:
            break
        interval = min(delay, remaining)
        logger.info("⏳ A DNS rekord még nem elérhető, várakozás (%ss)...", interval)
        try:
            async with asyncio.timeout(remaining):
                await pause(interval)
        except TimeoutError:
            break

    raise TimeoutError(
        f"Időtúllépés: A DNS rekord nem propagált {timeout} másodpercen belül."
    )


class SslService:
    def __init__(
        self,
        ddns_service: DDNSService,
    ):
        self._ddns_service = ddns_service
        self._in_progress = False

    async def get_local_ip_certificate(self, host_ip: str) -> SelfSignedCertificate:
        url = "https://local-ip.medicmobile.org/keys"
        try:
            logger.info(
                "🔒 Lekérjük a nyilvános local-ip.medicmobile.org SSL tanúsítványt..."
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            fullchain = data["fullchain"]
            privkey = data["privkey"]

            cert = x509.load_pem_x509_certificate(fullchain.encode("utf-8"))
            expires_at = int(cert.not_valid_after_utc.timestamp())

            logger.info(
                "✅ Sikeresen letöltve a nyilvános local-ip.medicmobile.org SSL tanúsítvány!"
            )

            return SelfSignedCertificate(
                fullchain=fullchain,
                privkey=privkey,
                expires_at=expires_at,
            )
        except Exception as exc:
            logger.error("operation=local-certificate fallback=self-signed %s", network_error_fields(exc))
            return self._generate_self_signed_certificate_fallback(host_ip)

    def _generate_self_signed_certificate_fallback(
        self, host_ip: str
    ) -> SelfSignedCertificate:
        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, host_ip),
                ]
            )

            ip_addr = ipaddress.ip_address(host_ip)
            alt_name = x509.SubjectAlternativeName([x509.IPAddress(ip_addr)])

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
                .not_valid_after(
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(days=365)
                )
                .add_extension(alt_name, critical=False)
                .sign(private_key, hashes.SHA256())
            )

            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )

            fullchain = cert_pem.decode("utf-8")
            privkey = key_pem.decode("utf-8")
            expires_at = int(cert.not_valid_after_utc.timestamp())

            return SelfSignedCertificate(
                fullchain=fullchain,
                privkey=privkey,
                expires_at=expires_at,
            )
        except Exception as err:
            logger.error(
                "Hiba történt a self-signed tanúsítvány generálásakor: %s", err
            )
            raise

    async def generate_acme_certificate(
        self,
        payload: AcmeCertificateGenerate,
    ) -> AcmeCertificate:
        try:
            return await self._generate_acme_certificate(payload)
        except TimeoutError:
            raise TimeoutError("Az ACME tanúsítvány-művelet időtúllépés miatt megszakadt.") from None
        except Exception as error:
            raise ValueError(f"ACME certificate operation failed: {network_error_fields(error)}") from None

    async def _generate_acme_certificate(
        self,
        payload: AcmeCertificateGenerate,
    ) -> AcmeCertificate:
        provider_id = payload.ddns_provider_id
        token = payload.ddns_provider_token
        host = payload.host

        # 1. Fiók kulcs betöltése (DB-ből) vagy új generálása
        if payload.account_key_pem:
            account_key_bytes = payload.account_key_pem.encode("utf-8")
            account_key = serialization.load_pem_private_key(
                account_key_bytes, password=None
            )
        else:
            account_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            account_key_bytes = account_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )

        # ACME kliens előkészítése
        jwk_key = jwk.JWKRSA(key=account_key)
        net = client.ClientNetwork(jwk_key)
        acme_client = client.ClientV2(
            client.ClientV2.get_directory(config.acme_directory_url, net), net=net
        )

        # Regisztráció / Bejelentkezés
        new_registration = messages.NewRegistration.from_data(
            email=payload.email,
            terms_of_service_agreed=True,
        )
        try:
            registration = acme_client.new_account(new_registration)
        except acme_errors.ConflictError as e:
            registration = acme_client.query_registration(
                messages.RegistrationResource(
                    uri=e.location,
                    body=messages.Registration(),
                )
            )
        except Exception as e:
            raise ValueError(f"Hiba történt az ACME fiók igénylése során: {network_error_fields(e)}") from None

        acme_client.net.account = registration

        # CSR (Certificate Signing Request) generálása a host-hoz
        cert_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        cert_private_key_pem = cert_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, payload.host),
                    ]
                )
            )
            .sign(cert_private_key, hashes.SHA256())
        )
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        # Új rendelés létrehozása
        order = acme_client.new_order(csr_pem)

        # authorizations típusának explicit megadása, hogy a Pyright megértse

        authorizations = cast(
            list[messages.AuthorizationResource], order.authorizations
        )

        # dns-01 challenge keresése az order-ben
        dns_challenge: messages.ChallengeBody | None = None
        for authz in authorizations:
            challenges_list = cast(
                tuple[messages.ChallengeBody, ...], authz.body.challenges
            )
            for chal in challenges_list:
                if chal.chall.typ == "dns-01":
                    dns_challenge = chal
                    break
            if dns_challenge:
                break

        if not dns_challenge:
            raise ValueError("Nem található dns-01 ACME kihívás Let's Encrypt oldalán!")

        # Kulcs-autorizáció generálása
        dns_chall = cast(challenges.DNS01, dns_challenge.chall)
        key_authorization = dns_chall.validation(jwk_key)

        try:
            # 2. Challenge kihelyezése a DNS szolgáltatónál (TXT rekord)
            logger.info(
                "📡 TXT rekord kihelyezése Let's Encrypt ACME hitelesítéshez..."
            )
            await self._ddns_service.update(
                provider_id=provider_id,
                payload=DDNSTxtUpdate(
                    provider_token=token,
                    host=host,
                    txt=key_authorization,
                ),
            )

            # Várakozás a DNS rekord propagálására
            logger.info("⏱️ Várakozás a DNS rekord propagálására...")
            await wait_for_dns_propagation(host=host, expected_txt=key_authorization)

            # Válaszolunk a kihívásra Let's Encrypt felé
            response = dns_chall.response(jwk_key)
            acme_client.answer_challenge(dns_challenge, response)

            # Order bevégzése és megvárása (poll)
            logger.info("🔒 ACME rendelés pollolása és véglegesítése...")
            finalized_order = acme_client.poll_and_finalize(order)

            # Letöltjük a teljes láncot
            fullchain_pem = finalized_order.fullchain_pem.encode("utf-8")

            # Lejárati idő kiszámítása
            cert = x509.load_pem_x509_certificate(fullchain_pem)
            expires_at = int(cert.not_valid_after_utc.timestamp())

            return AcmeCertificate(
                fullchain=fullchain_pem.decode("utf-8"),
                privkey=cert_private_key_pem.decode("utf-8"),
                expires_at=expires_at,
                account_key=account_key_bytes.decode("utf-8"),
            )

        finally:
            # 3. Clean up: challenge rekord eltávolítása a DNS-ből
            logger.info("🧹 ACME challenge TXT rekord takarítása a DNS-ből...")
            try:
                await self._ddns_service.update(
                    provider_id=provider_id,
                    payload=DDNSTxtUpdate(
                        provider_token=token,
                        host=host,
                        txt=key_authorization,
                        clear_txt=True,
                    ),
                )
            except Exception as cleanup_err:
                logger.warning(
                    "operation=acme-txt-cleanup %s", network_error_fields(cleanup_err)
                )
