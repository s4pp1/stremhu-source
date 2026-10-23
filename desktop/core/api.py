import httpx

from server.modules.system.schemas.api import SystemStatusResponse


def fetch_system_status(
    port: int = 7070, timeout: float = 1.0
) -> SystemStatusResponse | None:
    """Lekéri a StremHU Server rendszerállapotát a REST API-n keresztül (/api/system/status)."""
    url = f"https://127.0.0.1:{port}/api/system/status"
    try:
        with httpx.Client(
            verify=False,
            headers={"User-Agent": "StremHU-Desktop"},
            timeout=timeout,
        ) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return SystemStatusResponse.model_validate(resp.json())
    except Exception:
        return None
    return None
