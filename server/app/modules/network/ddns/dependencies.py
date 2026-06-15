from functools import lru_cache

from app.modules.network.ddns.service import DDNSService


@lru_cache(maxsize=1)
def create_ddns_service() -> DDNSService:
    """Létrehozza a DDNSService globális példányát (Singleton)."""
    return DDNSService()


def get_ddns_service() -> DDNSService:
    """FastAPI függőség-injektáló provider a DDNSService példányosításához."""
    return create_ddns_service()
