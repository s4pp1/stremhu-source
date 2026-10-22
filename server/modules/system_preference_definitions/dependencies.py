from sqlalchemy.orm import Session

from server.modules.attributes.dependencies import create_attributes_service
from server.modules.preference_definitions.dependencies import (
    create_preference_definitions_service,
)
from server.modules.system_preference_definitions.repository import (
    SystemPreferenceDefinitionsRepository,
)
from server.modules.system_preference_definitions.service import (
    SystemPreferenceDefinitionsService,
)


def create_system_preference_definitions_service(
    db: Session,
):
    system_preference_definitions_repository = SystemPreferenceDefinitionsRepository(db)
    preference_definitions_service = create_preference_definitions_service(db)
    attributes_service = create_attributes_service(db)

    return SystemPreferenceDefinitionsService(
        system_preference_definitions_repository,
        preference_definitions_service,
        attributes_service,
    )
