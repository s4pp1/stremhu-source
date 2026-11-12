from app.common.database import db_session
from app.common.logger import logger
from app.modules.storage.dependencies import create_storage_service


def run_storage_check(
    extra_bytes: int = 0,
    protected_info_hashes: set[str] | None = None,
) -> None:
    """Ellenőrzi a szabad helyet, és szükség esetén törli a seedben tartott,
    már törölhető torrenteket (legrégebben használttal kezdve)."""
    try:
        with db_session() as db:
            create_storage_service(db).ensure_free_space(
                extra_bytes=extra_bytes,
                protected_info_hashes=protected_info_hashes,
            )
    except Exception:
        logger.exception("‼️ Hiba történt a tárhely ellenőrzése során.")
