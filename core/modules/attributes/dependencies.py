from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.common.database import get_db
from core.modules.attributes.repository import AttributesRepository
from core.modules.attributes.service import AttributesService


def create_attributes_service(db: Session) -> AttributesService:
    repository = AttributesRepository(db)
    return AttributesService(repository)


def get_attributes_service(
    db: Annotated[Session, Depends(get_db)],
) -> AttributesService:
    return create_attributes_service(db)
