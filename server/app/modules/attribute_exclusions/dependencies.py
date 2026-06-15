from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.attribute_exclusions.repository import AttributeExclusionsRepository
from app.modules.attribute_exclusions.service import AttributeExclusionsService


def create_attribute_exclusions_service(db: Session) -> AttributeExclusionsService:
    repository = AttributeExclusionsRepository(db)
    return AttributeExclusionsService(repository)


def get_attribute_exclusions_service(
    db: Annotated[Session, Depends(get_db)],
) -> AttributeExclusionsService:
    return create_attribute_exclusions_service(db)
