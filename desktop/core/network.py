import ipaddress
import socket

import psutil


def check_interface_internet(ip: str, timeout: float = 0.3) -> bool:
    """Megvizsgálja, hogy az adott helyi IP-címhez tartozó interfészen keresztül elérhető-e az internet."""
    for target in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.bind((ip, 0))
                s.connect(target)
                return True
        except Exception:
            continue
    return False


def get_local_ip() -> str:
    """Megállapítja a gép tényleges helyi hálózati (LAN) IP címét a Desktop környezetben.

    A psutil segítségével lekérdezi a fizikai és aktív hálózati interfészeket a gazdagépen,
    ellenőrzi az internetkapcsolatot az adott csatolón, és a valós hálózati forgalom
    (I/O számláló) és kapcsolati sebesség alapján kiválasztja az elsődleges privát IPv4 címet.
    """
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io = psutil.net_io_counters(pernic=True)

        candidates: list[tuple[int, int, str]] = []

        for name, addr_list in addrs.items():
            st = stats.get(name)
            ioc = io.get(name)

            # Csak aktív, nem loopback és nem point-to-point (VPN tunnel) interfészek
            if not st or not st.isup:
                continue
            flags = getattr(st, "flags", "")
            if "loopback" in flags or "pointopoint" in flags:
                continue

            for a in addr_list:
                if a.family == socket.AF_INET:
                    ip = ipaddress.ip_address(a.address)
                    if ip.is_private and not ip.is_loopback:
                        traffic = (ioc.bytes_sent + ioc.bytes_recv) if ioc else 0
                        speed = st.speed or 0
                        candidates.append((traffic, speed, a.address))

        if candidates:
            # Megvizsgáljuk, melyik interfészen működik ténylegesen internetelérés
            ranked_candidates = [
                (1 if check_interface_internet(addr) else 0, traffic, speed, addr)
                for traffic, speed, addr in candidates
            ]
            # Prioritás: 1. Van internet, 2. Forgalom mennyisége, 3. Kapcsolati sebesség
            ranked_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            return ranked_candidates[0][3]
    except Exception:
        pass

    # 1. Fallback: routing lekérdezés privát broadcast címmel (offline LAN-on is működik)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    # 2. Fallback: gép hostname alapján
    try:
        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
        for ip in ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"
