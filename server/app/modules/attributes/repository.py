from sqlalchemy.orm import Session

from app.modules.attributes.models import AttributeModel


class AttributesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self) -> list[AttributeModel]:
        """Fetches all attributes from the database."""
        return self.db.query(AttributeModel).order_by(AttributeModel.order.asc()).all()

    def find_by_preference(self, preference_id: str) -> list[AttributeModel]:
        """Fetches all attributes belonging to a specific preference category."""
        return (
            self.db.query(AttributeModel)
            .filter(AttributeModel.preference_id == preference_id)
            .order_by(AttributeModel.order.asc())
            .all()
        )

    def find_by_id(self, attribute_id: str) -> AttributeModel | None:
        """Finds a single attribute by its ID."""
        return (
            self.db.query(AttributeModel)
            .filter(AttributeModel.id == attribute_id)
            .first()
        )

    def add(self, attribute: AttributeModel) -> None:
        """Adds a new attribute entity to the session."""
        self.db.add(attribute)

    def commit(self) -> None:
        """Commits the active database transaction."""
        self.db.commit()
