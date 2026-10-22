from functools import lru_cache

from server.modules.relay.service import RelayService


@lru_cache(maxsize=1)
def get_relay_service() -> RelayService:
    return RelayService()
