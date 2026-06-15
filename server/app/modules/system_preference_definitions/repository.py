from sqlalchemy.orm import Session, joinedload

from app.modules.preference_definitions.models import (
    PreferenceDefinitionAttributeModel,
    PreferenceDefinitionModel,
)
from app.modules.system_preference_definitions.models import (
    SystemPreferenceDefinitionModel,
)


class SystemPreferenceDefinitionsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        preference_definition_id: str,
        order: int,
    ) -> SystemPreferenceDefinitionModel:
        system_preference_definition = SystemPreferenceDefinitionModel(
            definition_id=preference_definition_id,
            order=order,
        )

        self.db.add(system_preference_definition)
        self.db.flush()

        return system_preference_definition

    def find_list(self) -> list[SystemPreferenceDefinitionModel]:
        """Fetches all system preferences sorted by order priority with eager-loaded attributes."""
        return (
            self.db.query(SystemPreferenceDefinitionModel)
            .options(
                joinedload(SystemPreferenceDefinitionModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(SystemPreferenceDefinitionModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .order_by(SystemPreferenceDefinitionModel.order.asc())
            .all()
        )

    def find_by_id(
        self,
        id: str,
    ) -> SystemPreferenceDefinitionModel | None:
        """Finds a specific system preference by category with eager-loaded attributes."""
        return (
            self.db.query(SystemPreferenceDefinitionModel)
            .filter(SystemPreferenceDefinitionModel.definition_id == id)
            .options(
                joinedload(SystemPreferenceDefinitionModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(SystemPreferenceDefinitionModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .first()
        )

    def find_by_preference_id(
        self,
        preference_id: str,
    ) -> SystemPreferenceDefinitionModel | None:
        """Finds a specific system preference by preference with eager-loaded attributes."""
        return (
            self.db.query(SystemPreferenceDefinitionModel)
            .options(
                joinedload(SystemPreferenceDefinitionModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(SystemPreferenceDefinitionModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .join(SystemPreferenceDefinitionModel.definition)
            .filter(PreferenceDefinitionModel.preference_id == preference_id)
            .first()
        )

    def delete(self, entity) -> None:
        """Deletes a specific entity from the database."""
        self.db.delete(entity)
        self.db.flush()

    def reorder(
        self,
        updates: list[tuple[SystemPreferenceDefinitionModel, int]],
    ) -> list[SystemPreferenceDefinitionModel]:
        """Updates the priority order of system preferences and flushes changes."""
        for model, order in updates:
            model.order = order

        self.db.flush()

        for model, _ in updates:
            self.db.expire(model)
        return self.find_list()
