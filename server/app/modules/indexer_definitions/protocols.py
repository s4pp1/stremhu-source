from typing import Protocol

from app.modules.indexer_definitions.schemas.internal import IndexerDefinitionLogin


class IndexerAccountStorage(Protocol):
    def get_credentials(self, indexer_id: str) -> IndexerDefinitionLogin | None:
        """Lekéri az indexer hitelesítési adatait és a tárolt cookie-kat."""
        ...

    def save_cookies(self, indexer_id: str, cookies: dict[str, str]) -> None:
        """Elmenti a frissített session cookie-kat az adatbázisba."""
        ...
