from functools import lru_cache

from core.modules.relay.service import RelayService


@lru_cache(maxsize=1)
def get_relay_service() -> RelayService:
    return RelayService()
