from app.modules.attributes.models import AttributeModel
from app.modules.attributes.repository import AttributesRepository


class AttributesService:
    def __init__(self, repository: AttributesRepository):
        """Initializes the service with the attributes repository."""
        self._repository = repository

    def find_list(self) -> list[AttributeModel]:
        """Returns all attributes from the database."""
        return self._repository.find_all()

    def get_by_preference(self, preference_id: str) -> list[AttributeModel]:
        """Returns all attributes for a given preference ID."""
        return self._repository.find_by_preference(preference_id)

    def get_all_as_map(self) -> dict[str, AttributeModel]:
        """Returns all attributes as a dictionary indexed by their ID."""
        attributes = self._repository.find_all()
        return {attr.id: attr for attr in attributes}
