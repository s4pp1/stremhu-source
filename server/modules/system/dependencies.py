from modules.system.service import SystemService


def create_system_service() -> SystemService:
    """Létrehozza a SystemService példányát."""
    return SystemService()


def get_system_service() -> SystemService:
    """FastAPI függőség-injektáló provider a SystemService példányosításához."""
    return create_system_service()
