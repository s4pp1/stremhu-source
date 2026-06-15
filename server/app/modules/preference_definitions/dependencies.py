from sqlalchemy.orm import Session

from app.modules.attributes.dependencies import create_attributes_service
from app.modules.preference_definitions.repository import PreferenceDefinitionRepository
from app.modules.preference_definitions.service import PreferenceDefinitionsService


def create_preference_definitions_service(db: Session) -> PreferenceDefinitionsService:
    preference_definitions_repository = PreferenceDefinitionRepository(db)
    attributes_service = create_attributes_service(db)

    return PreferenceDefinitionsService(
        preference_definitions_repository,
        attributes_service,
    )
