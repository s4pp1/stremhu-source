from common.database import get_db
from fastapi import Depends
from modules.roles.service import RolesService
from sqlalchemy.orm import Session


def create_roles_service(db: Session) -> RolesService:
    return RolesService(db)


def get_roles_service(db: Session = Depends(get_db)) -> RolesService:
    return create_roles_service(db)
