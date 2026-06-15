import asyncio
import os
import socket
from pathlib import Path

from app.boot.schemas import BootNetworkConfig
from app.common.database import db_session
from app.config import config
from app.modules.network.dependencies import create_network_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.settings.enums import (
    NetworkModeEnum,
)
from app.modules.settings.schemas.internal import NetworkSettings


def get_network_settings() -> NetworkSettings:
    """Kiolvassa a hálózati beállításokat az adatbázisból."""
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)
            network_settings = settings_service.get_network()
            return network_settings
    except Exception as e:
        print(
            f"[FIGYELEM] Nem sikerült beolvasni a hálózati beállításokat az adatbázisból: {e}"
        )
        raise ValueError("Hálózati beállítások nem léteznek az adatbázisban.")


def write_certs_to_disk(fullchain: str, privkey: str) -> tuple[Path, Path]:
    """Lementi a tanúsítványokat a system/certs könyvtárba, és visszaadja a fájlok elérési útját."""

    cert_path = config.certificates_dir / "fullchain.pem"
    key_path = config.certificates_dir / "privkey.pem"

    cert_path.write_text(fullchain, encoding="utf-8")
    key_path.write_text(privkey, encoding="utf-8")

    return cert_path, key_path


def _ensure_db_network_settings(host_ip: str) -> NetworkSettings:
    with db_session() as db:
        settings_service = create_settings_service(db)
        network_service = create_network_service(db)
        network_settings = settings_service.find_network()

        if network_settings and network_settings.mode != NetworkModeEnum.LOCAL:
            return network_settings

        local_settings, _ = asyncio.run(network_service.setup_local())
        settings_service.save_network(local_settings)

        return local_settings


def _check_host_ip(host_ip: str) -> str:
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.connect((host_ip, 9))
        test_sock.close()
    except Exception as e:
        raise ValueError(
            f"🚨 Hiba: A megadott HOST_IP ({host_ip}) hálózati szinten nem érhető el a konténerből! Részletek: {e}"
        )

    # 4. Helyi IP-cím tulajdonjog ellenőrzése (csak ha nem Docker konténerben futunk)
    is_in_docker = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
    if not is_in_docker:
        try:
            bind_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bind_sock.bind((host_ip, 0))
            bind_sock.close()
        except Exception:
            raise ValueError(
                f"🚨 Hiba: A megadott HOST_IP ({host_ip}) nem ehhez a számítógéphez tartozik! "
                "Kérlek a saját géped valódi helyi IP-címét add meg!"
            )

    return host_ip


def ensure_network_settings() -> BootNetworkConfig:
    host_ip = _check_host_ip(config.host_ip)

    network_settings = _ensure_db_network_settings(host_ip)

    cert_path_str: str | None = None
    key_path_str: str | None = None

    if network_settings.mode != NetworkModeEnum.MANUAL:
        cert_path, key_path = write_certs_to_disk(
            fullchain=network_settings.fullchain,
            privkey=network_settings.privkey,
        )

        cert_path_str = str(cert_path)
        key_path_str = str(key_path)

    return BootNetworkConfig(
        network_settings=network_settings,
        cert_path=cert_path_str,
        key_path=key_path_str,
    )
