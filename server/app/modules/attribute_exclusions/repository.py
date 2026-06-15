from sqlalchemy.orm import Session

from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.attribute_exclusions.schemas.internal import (
    AttributeExclusionCreate,
    AttributeExclusionFilter,
)
from app.modules.media_attributes.models import MediaAttributeModel


class AttributeExclusionsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        payload: AttributeExclusionCreate,
    ) -> AttributeExclusionModel:
        model = AttributeExclusionModel(**payload.model_dump())

        self.db.add(model)
        self.db.flush()

        return model

    def find_list(
        self,
        filter: AttributeExclusionFilter | None = None,
    ) -> list[AttributeExclusionModel]:
        query = self.db.query(AttributeExclusionModel).join(
            AttributeExclusionModel.attribute
        )

        if filter:
            if filter.attribute_id:
                query = query.filter(
                    AttributeExclusionModel.attribute_id == filter.attribute_id
                )
            if filter.user_id:
                query = query.filter(AttributeExclusionModel.user_id == filter.user_id)

        return query.order_by(MediaAttributeModel.order.asc()).all()

    def find_by_id(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> AttributeExclusionModel | None:
        return (
            self.db.query(AttributeExclusionModel)
            .filter_by(attribute_id=attribute_id, user_id=user_id)
            .first()
        )

    def delete(
        self,
        attribute_id: str,
        user_id: str | None,
    ) -> None:
        self.db.query(AttributeExclusionModel).filter_by(
            attribute_id=attribute_id, user_id=user_id
        ).delete()
