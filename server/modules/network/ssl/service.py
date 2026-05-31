import datetime
import ipaddress

from acme import challenges, client, errors as acme_errors, messages
from common.logger import logger
from config import config
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from josepy import jwk
from modules.network.ddns.schemas import DDNSTxtUpdate
from modules.network.ddns.service import DDNSService
from modules.network.ssl.schemas import (
    AcmeCertificate,
    AcmeCertificateGenerate,
    SelfSignedCertificate,
)


class SslService:
    def __init__(
        self,
        ddns_service: DDNSService,
    ):
        self._ddns_service = ddns_service
        self._in_progress = False

    def generate_self_signed_certificate(self, host_ip: str) -> SelfSignedCertificate:
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
        except Exception as e:
            logger.error("Hiba történt a self-signed tanúsítvány generálásakor: %s", e)
            raise

    async def generate_acme_certificate(
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
        try:
            acme_client.new_account(
                messages.NewRegistration.from_data(
                    email=payload.email,
                    terms_of_service_agreed=True,
                )
            )
        except acme_errors.ConflictError:
            pass
        except Exception as e:
            raise ValueError(f"Hiba történt az ACME fiók igénylése során: {e}") from e

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
        from typing import cast

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

            # Várjunk 20 másodpercet a DNS rekord propagálására
            logger.info("⏱️ Várakozás a DNS rekord propagálására (20s)...")
            import asyncio

            await asyncio.sleep(20)

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
                    "Nem sikerült törölni a DNS TXT rekordot: %s", cleanup_err
                )
