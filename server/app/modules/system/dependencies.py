from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.roles.dependencies import create_roles_service
from app.modules.settings.dependencies import create_settings_service
from app.modules.system.service import SystemService
from app.modules.users.dependencies import create_users_service


def create_system_service(db: Session) -> SystemService:
    settings_service = create_settings_service(db)
    users_service = create_users_service(db)
    roles_service = create_roles_service(db)

    return SystemService(
        settings_service=settings_service,
        users_service=users_service,
        roles_service=roles_service,
    )


def get_system_service(
    db: Annotated[Session, Depends(get_db)],
) -> SystemService:
    return create_system_service(db)
