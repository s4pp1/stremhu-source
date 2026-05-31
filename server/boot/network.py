import os
import socket
from pathlib import Path

from boot.schemas import BootNetworkConfig
from common.database import db_session
from config import config
from modules.network.dependencies import create_network_service
from modules.settings.dependencies import create_settings_service
from modules.settings.schemas import (
    NetworkModeEnum,
    NetworkSettings,
)


def get_network_settings() -> NetworkSettings:
    """Kiolvassa a hálózati beállításokat az adatbázisból."""
    try:
        with db_session() as db:
            settings_service = create_settings_service(db)
            network_settings = settings_service.get_network_or_raise()
            return network_settings
    except Exception as e:
        print(
            f"[FIGYELEM] Nem sikerült beolvasni a hálózati beállításokat az adatbázisból: {e}"
        )
        raise ValueError("Hálózati beállítások nem léteznek az adatbázisban.")


def write_certs_to_disk(fullchain: str, privkey: str) -> tuple[Path, Path]:
    """Lementi a tanúsítványokat a system/certs könyvtárba, és visszaadja a fájlok elérési útját."""
    certs_dir = config.system_dir / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)

    cert_path = certs_dir / "fullchain.pem"
    key_path = certs_dir / "privkey.pem"

    cert_path.write_text(fullchain, encoding="utf-8")
    key_path.write_text(privkey, encoding="utf-8")

    return cert_path, key_path


def _ensure_db_network_settings(host_ip: str) -> NetworkSettings:
    """Ellenőrzi az adatbázisban a hálózati beállításokat, és szükség esetén generálja a tanúsítványt."""
    from common.database import db_session
    from modules.settings.dependencies import create_settings_service

    with db_session() as db:
        settings_service = create_settings_service(db)
        network_service = create_network_service(db)
        network_settings = settings_service.get_network()

        # ÖNGYÓGYÍTÓ LOGIKA (Self-healing recovery):
        # Ha MANUAL módban vagyunk, nincs reverse_proxy, de az egyedi tanúsítványfájlok hiányoznak,
        # akkor a felhasználó kizárásának elkerülése érdekében automatikusan visszaváltunk LOCAL módra a DB-ben!
        if (
            network_settings
            and network_settings.mode == NetworkModeEnum.MANUAL
            and not network_settings.reverse_proxy
        ):
            custom_dir = config.system_dir / "certs" / "custom"
            cert_path = custom_dir / "fullchain.pem"
            key_path = custom_dir / "privkey.pem"

            if not cert_path.exists() or not key_path.exists():
                print(
                    "\n🚨 [HIBA] Kézi (manual) SSL mód van beállítva, de a tanúsítványok nem találhatók a megadott helyen!\n"
                    f"   Elvárt elérési út: {cert_path} és {key_path}\n"
                    "🔄 [ÖNGYÓGYÍTÁS] A felhasználói kizárás megelőzése érdekében a rendszer automatikusan\n"
                    "   visszaállítja a Helyi (Local) ön-aláírt SSL módot az adatbázisban...\n"
                )

                local_settings, _ = network_service.setup_local()
                settings_service.save_network(local_settings)
                network_settings = local_settings
                return network_settings

        if network_settings and network_settings.mode != NetworkModeEnum.LOCAL:
            return network_settings

        if network_settings and network_settings.ip == host_ip:
            return network_settings

        local_settings, _ = network_service.setup_local()
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
    """
    Ellenőrzi, inicializálja és feloldja a hálózati és SSL beállításokat.

    Returns:
        BootNetworkConfig: A rendszerindításhoz feloldott hálózati és SSL konfigurációs modell.
    """

    host_ip = _check_host_ip(config.host_ip)

    network_settings = _ensure_db_network_settings(host_ip)

    cert_path_str: str | None = None
    key_path_str: str | None = None
    mode = network_settings.mode
    host = network_settings.host

    # Kézi (manual) SSL mód
    if (
        network_settings.mode == NetworkModeEnum.MANUAL
        and not network_settings.reverse_proxy
    ):
        custom_dir = config.system_dir / "certs" / "custom"
        cert_path = custom_dir / "fullchain.pem"
        key_path = custom_dir / "privkey.pem"

        if cert_path.exists() and key_path.exists():
            cert_path_str = str(cert_path)
            key_path_str = str(key_path)
            host = network_settings.host

    # Generált tanúsítványos mód (LOCAL / AUTO)
    if (
        network_settings.mode == NetworkModeEnum.LOCAL
        or network_settings.mode == NetworkModeEnum.AUTO
    ):
        cert_path, key_path = write_certs_to_disk(
            network_settings.fullchain, network_settings.privkey
        )
        cert_path_str = str(cert_path)
        key_path_str = str(key_path)
        host = network_settings.host

    return BootNetworkConfig(
        cert_path=cert_path_str,
        key_path=key_path_str,
        mode=mode,
        host=host,
    )
