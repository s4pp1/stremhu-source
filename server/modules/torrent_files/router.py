from fastapi import APIRouter, Depends
from modules.auth.dependencies import SessionGuard
from modules.roles.enums import UserRole
from modules.torrent_files.dependencies import get_torrent_files_service
from modules.torrent_files.service import TorrentFilesService
from modules.users.models import UserModel

router = APIRouter(
    prefix="/torrent-files",
    tags=["Torrent Files"],
)


@router.post(
    "/cleanup",
)
def cleanup(
    torrent_files_service: TorrentFilesService = Depends(get_torrent_files_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
):
    """Elindítja az elavult és inaktív torrent fájlok manuális törlését (Retention Cleanup)."""
    torrent_files_service.run_retention_cleanup(retention_seconds=0)
