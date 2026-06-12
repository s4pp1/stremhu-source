from common.database import get_db
from fastapi import Depends
from modules.attribute_exclusions.repository import AttributeExclusionsRepository
from modules.attribute_exclusions.service import AttributeExclusionsService
from sqlalchemy.orm import Session


def create_attribute_exclusions_service(db: Session) -> AttributeExclusionsService:
    repository = AttributeExclusionsRepository(db)
    return AttributeExclusionsService(repository)


def get_attribute_exclusions_service(
    db: Session = Depends(get_db),
) -> AttributeExclusionsService:
    return create_attribute_exclusions_service(db)
