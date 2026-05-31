from modules.network.ddns.service import DDNSService


def create_ddns_service() -> DDNSService:
    """Létrehozza a DDNSService példányát."""
    return DDNSService()


def get_ddns_service() -> DDNSService:
    """FastAPI függőség-injektáló provider a DDNSService példányosításához."""
    return create_ddns_service()
