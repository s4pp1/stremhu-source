from sqlalchemy.orm import Session

from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.schemas.internal import MediaAttributeFilter
from app.modules.preference_definitions.models import (
    PreferenceDefinitionAttributeModel,
)
from app.modules.user_preference_definitions.models import (
    UserPreferenceDefinitionModel,
)


class MediaAttributesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_list(
        self,
        filter: MediaAttributeFilter | None = None,
    ) -> list[MediaAttributeModel]:
        query = self.db.query(MediaAttributeModel)

        if filter:
            if filter.user_id:
                from app.modules.attribute_exclusions.models import (
                    AttributeExclusionModel,
                )

                exclusion_subquery = (
                    self.db.query(AttributeExclusionModel.attribute_id)
                    .filter(AttributeExclusionModel.user_id == filter.user_id)
                    .scalar_subquery()
                )
                query = query.filter(~MediaAttributeModel.id.in_(exclusion_subquery))

                if filter.not_added_to_preference:
                    pref_attr_subquery = (
                        self.db.query(PreferenceDefinitionAttributeModel.attribute_id)
                        .join(
                            UserPreferenceDefinitionModel,
                            UserPreferenceDefinitionModel.definition_id
                            == PreferenceDefinitionAttributeModel.definition_id,
                        )
                        .filter(UserPreferenceDefinitionModel.user_id == filter.user_id)
                        .scalar_subquery()
                    )
                    query = query.filter(
                        ~MediaAttributeModel.id.in_(pref_attr_subquery)
                    )

        return query.order_by(MediaAttributeModel.order.asc()).all()

    def find_excluding_ids(self, ids: set[str]) -> list[MediaAttributeModel]:
        return (
            self.db.query(MediaAttributeModel)
            .filter(~MediaAttributeModel.id.in_(ids))
            .all()
        )

    def delete_excluding_ids(self, ids: set[str]) -> int:
        to_delete = self.find_excluding_ids(ids)
        count = len(to_delete)
        for attr in to_delete:
            self.db.delete(attr)
        return count

    def add(self, attribute: MediaAttributeModel) -> None:
        self.db.add(attribute)
