from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.modules.preference_definitions.models import (
    PreferenceDefinitionAttributeModel,
    PreferenceDefinitionModel,
)
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel


class UserPreferenceDefinitionsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        preference_definition_id: str,
        user_id: str,
        order: int,
    ) -> UserPreferenceDefinitionModel:
        user_preference_definition = UserPreferenceDefinitionModel(
            user_id=user_id,
            definition_id=preference_definition_id,
            order=order,
        )

        self.db.add(user_preference_definition)
        self.db.flush()

        return user_preference_definition

    def find_list(
        self,
        user_id: str,
    ) -> list[UserPreferenceDefinitionModel]:
        """Fetches all user preferences sorted by order priority with eager-loaded attributes."""
        return (
            self.db.query(UserPreferenceDefinitionModel)
            .options(
                joinedload(UserPreferenceDefinitionModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(UserPreferenceDefinitionModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .filter(UserPreferenceDefinitionModel.user_id == user_id)
            .order_by(UserPreferenceDefinitionModel.order.asc())
            .all()
        )

    def find_by_id(
        self,
        user_id: str,
        preference_id: str,
    ) -> UserPreferenceDefinitionModel | None:
        """Finds a specific user preference by category with eager-loaded attributes."""
        return (
            self.db.query(UserPreferenceDefinitionModel)
            .options(
                joinedload(UserPreferenceDefinitionModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(UserPreferenceDefinitionModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .join(UserPreferenceDefinitionModel.definition)
            .filter(
                and_(
                    UserPreferenceDefinitionModel.user_id == user_id,
                    PreferenceDefinitionModel.preference_id == preference_id,
                )
            )
            .first()
        )

    def delete(self, user_preference: UserPreferenceDefinitionModel) -> None:
        """Deletes a specific entity from the database."""
        self.db.delete(user_preference)
        self.db.flush()

    def reorder(
        self, user_id: str, updates: list[tuple[UserPreferenceDefinitionModel, int]]
    ) -> list[UserPreferenceDefinitionModel]:
        """Updates the priority order of the user preferences and flushes changes."""
        for model, order in updates:
            model.order = order
        self.db.flush()
        for model, _ in updates:
            self.db.expire(model)
        return self.find_list(user_id)
