from modules.preferences.enums import PreferenceEnum
from modules.preferences.models import (
    PreferenceDefinitionAttributeModel,
    PreferenceDefinitionModel,
    SystemPreferenceModel,
    UserPreferenceModel,
)
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload


class UserPreferencesRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        preference: PreferenceEnum,
        preferred_attribute_ids: list[str],
        order: int,
    ) -> UserPreferenceModel:
        preference_definition = PreferenceDefinitionModel(preference_id=preference)
        self.db.add(preference_definition)

        for idx, attr_id in enumerate(preferred_attribute_ids):
            preference_definition_attribute = PreferenceDefinitionAttributeModel(
                definition_id=preference_definition.id, attribute_id=attr_id, order=idx
            )
            self.db.add(preference_definition_attribute)

        user_preference = UserPreferenceModel(
            user_id=user_id, definition_id=preference_definition.id, order=order
        )
        self.db.add(user_preference)
        self.db.flush()

        created_user_preference = self.find_one_by_preference(user_id, preference)
        assert created_user_preference is not None
        return created_user_preference

    def find_by_user_id(self, user_id: str) -> list[UserPreferenceModel]:
        """Fetches all user preferences sorted by order priority with eager-loaded attributes."""
        return (
            self.db.query(UserPreferenceModel)
            .options(
                joinedload(UserPreferenceModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(UserPreferenceModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .filter(UserPreferenceModel.user_id == user_id)
            .order_by(UserPreferenceModel.order.asc())
            .all()
        )

    def find_one_by_preference(
        self, user_id: str, preference: PreferenceEnum
    ) -> UserPreferenceModel | None:
        """Finds a specific user preference by category with eager-loaded attributes."""
        return (
            self.db.query(UserPreferenceModel)
            .options(
                joinedload(UserPreferenceModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(UserPreferenceModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .join(UserPreferenceModel.definition)
            .filter(
                and_(
                    UserPreferenceModel.user_id == user_id,
                    PreferenceDefinitionModel.preference_id == preference,
                )
            )
            .first()
        )

    def update(
        self,
        user_preference: UserPreferenceModel,
        preferred_attribute_ids: list[str],
    ) -> UserPreferenceModel:
        definition = user_preference.definition
        self.delete_definition_attributes(definition.id)

        for idx, preferred_attribute_id in enumerate(preferred_attribute_ids):
            pref_attr = PreferenceDefinitionAttributeModel(
                definition_id=definition.id,
                attribute_id=preferred_attribute_id,
                order=idx,
            )
            self.db.add(pref_attr)

        self.db.flush()
        self.db.expire(definition)

        updated_user_preference = self.find_one_by_preference(
            user_preference.user_id, definition.preference_id
        )
        assert updated_user_preference is not None
        return updated_user_preference

    def delete(self, user_preference: UserPreferenceModel) -> None:
        """Deletes a specific entity from the database."""
        self.db.delete(user_preference)
        self.db.flush()

    def reorder(
        self, user_id: str, updates: list[tuple[UserPreferenceModel, int]]
    ) -> list[UserPreferenceModel]:
        """Updates the priority order of the user preferences and flushes changes."""
        for model, order in updates:
            model.order = order
        self.db.flush()
        for model, _ in updates:
            self.db.expire(model)
        return self.find_by_user_id(user_id)

    def delete_definition_attributes(self, definition_id: str) -> None:
        """Deletes all preferred attributes linked to a specific preference definition."""
        self.db.query(PreferenceDefinitionAttributeModel).filter(
            PreferenceDefinitionAttributeModel.definition_id == definition_id
        ).delete(synchronize_session=False)


class SystemPreferencesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self) -> list[SystemPreferenceModel]:
        """Fetches all system preferences sorted by order priority with eager-loaded attributes."""
        return (
            self.db.query(SystemPreferenceModel)
            .options(
                joinedload(SystemPreferenceModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(SystemPreferenceModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .order_by(SystemPreferenceModel.order.asc())
            .all()
        )

    def find_one_by_preference(
        self, preference: PreferenceEnum
    ) -> SystemPreferenceModel | None:
        """Finds a specific system preference by category with eager-loaded attributes."""
        return (
            self.db.query(SystemPreferenceModel)
            .options(
                joinedload(SystemPreferenceModel.definition).joinedload(
                    PreferenceDefinitionModel.preference
                ),
                joinedload(SystemPreferenceModel.definition)
                .joinedload(PreferenceDefinitionModel.definition_attributes)
                .joinedload(PreferenceDefinitionAttributeModel.attribute),
            )
            .join(SystemPreferenceModel.definition)
            .filter(PreferenceDefinitionModel.preference_id == preference)
            .first()
        )

    def delete(self, entity) -> None:
        """Deletes a specific entity from the database."""
        self.db.delete(entity)
        self.db.flush()

    def reorder(
        self, updates: list[tuple[SystemPreferenceModel, int]]
    ) -> list[SystemPreferenceModel]:
        """Updates the priority order of system preferences and flushes changes."""
        for model, order in updates:
            model.order = order
        self.db.flush()
        for model, _ in updates:
            self.db.expire(model)
        return self.find_all()

    def delete_definition_attributes(self, definition_id: str) -> None:
        """Deletes all preferred attributes linked to a specific preference definition."""
        self.db.query(PreferenceDefinitionAttributeModel).filter(
            PreferenceDefinitionAttributeModel.definition_id == definition_id
        ).delete(synchronize_session=False)

    def create(
        self,
        preference: PreferenceEnum,
        preferred_attribute_ids: list[str],
        order: int,
    ) -> SystemPreferenceModel:
        """Creates a new system preference category along with definition and preferred attributes."""
        definition = PreferenceDefinitionModel(preference_id=preference)
        self.db.add(definition)

        for idx, attr_id in enumerate(preferred_attribute_ids):
            pref_attr = PreferenceDefinitionAttributeModel(
                definition_id=definition.id, attribute_id=attr_id, order=idx
            )
            self.db.add(pref_attr)

        system_pref = SystemPreferenceModel(definition_id=definition.id, order=order)
        self.db.add(system_pref)

        # Flush so the database writes them, making them queryable for joinedload
        self.db.flush()

        # Query and return the eager-loaded joinedload object directly from repository
        result = self.find_one_by_preference(preference)
        assert result is not None
        return result

    def update(
        self,
        system_pref: SystemPreferenceModel,
        preferred_attribute_ids: list[str],
    ) -> SystemPreferenceModel:
        """Updates the preferred attribute list of an existing system preference."""
        definition = system_pref.definition
        self.delete_definition_attributes(definition.id)

        for idx, attr_id in enumerate(preferred_attribute_ids):
            pref_attr = PreferenceDefinitionAttributeModel(
                definition_id=definition.id, attribute_id=attr_id, order=idx
            )
            self.db.add(pref_attr)

        # Flush to DB and clear relationship cache to prevent returning stale in-memory cached state
        self.db.flush()
        self.db.expire(definition)

        # Query and return the eager-loaded joinedload object directly from repository
        result = self.find_one_by_preference(definition.preference_id)
        assert result is not None
        return result
