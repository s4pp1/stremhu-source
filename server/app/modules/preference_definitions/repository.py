from sqlalchemy.orm import Session

from app.modules.preference_definitions.models import (
    PreferenceDefinitionAttributeModel,
    PreferenceDefinitionModel,
)
from app.modules.preferences.schemas.internal import PreferenceCreate


class PreferenceDefinitionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PreferenceCreate) -> PreferenceDefinitionModel:
        preference_definition = PreferenceDefinitionModel(
            preference_id=payload.preference_id
        )
        self.db.add(preference_definition)

        for idx, attr_id in enumerate(payload.attribute_ids):
            preference_definition_attribute = PreferenceDefinitionAttributeModel(
                definition_id=preference_definition.id, attribute_id=attr_id, order=idx
            )
            self.db.add(preference_definition_attribute)

        self.db.flush()

        return preference_definition

    def find_by_id(
        self,
        preference_definition_id: str,
    ) -> PreferenceDefinitionModel | None:
        return (
            self.db.query(PreferenceDefinitionModel)
            .filter(PreferenceDefinitionModel.id == preference_definition_id)
            .first()
        )

    def find_by_attribute_id(
        self,
        attribute_id: str,
    ) -> list[PreferenceDefinitionModel]:
        return (
            self.db.query(PreferenceDefinitionModel)
            .join(PreferenceDefinitionModel.definition_attributes)
            .filter(PreferenceDefinitionAttributeModel.attribute_id == attribute_id)
            .all()
        )

    def update(
        self,
        preference_definition_id: str,
        attribute_ids: list[str],
    ) -> PreferenceDefinitionModel:
        self._delete_attributes(preference_definition_id)

        for idx, attribute_id in enumerate(attribute_ids):
            pref_attr = PreferenceDefinitionAttributeModel(
                definition_id=preference_definition_id,
                attribute_id=attribute_id,
                order=idx,
            )
            self.db.add(pref_attr)

        self.db.flush()

        updated_user_preference = self.find_by_id(preference_definition_id)
        assert updated_user_preference is not None

        self.db.expire(updated_user_preference)

        return updated_user_preference

    def delete(
        self,
        preference_definition_id: str,
    ) -> None:
        self.db.query(PreferenceDefinitionModel).filter(
            PreferenceDefinitionModel.id == preference_definition_id
        ).delete(synchronize_session=False)

        self.db.flush()

    def _delete_attributes(
        self,
        preference_definition_id: str,
    ) -> None:
        """Deletes all preferred attributes linked to a specific preference definition."""
        self.db.query(PreferenceDefinitionAttributeModel).filter(
            PreferenceDefinitionAttributeModel.definition_id == preference_definition_id
        ).delete(synchronize_session=False)
