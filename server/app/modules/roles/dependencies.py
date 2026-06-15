from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.roles.service import RolesService


def create_roles_service(db: Session) -> RolesService:
    return RolesService(db)


def get_roles_service(db: Annotated[Session, Depends(get_db)]) -> RolesService:
    return create_roles_service(db)
