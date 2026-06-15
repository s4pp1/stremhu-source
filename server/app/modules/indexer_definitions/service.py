import pydash
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.logger import logger
from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.integrations import discover_indexer_definitions
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.protocols import IndexerAccountStorage
from app.modules.preferences.constants import PreferenceKey


class IndexerDefinitionsService:
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ):
        self._definitions: dict[str, BaseIndexerDefinition] = {}

        for definition_class in discover_indexer_definitions():
            instance = definition_class(indexer_account_storage)
            self._definitions[instance.id] = instance

    def get_list(self, include_disabled: bool = False) -> list[BaseIndexerDefinition]:
        def get_sort_key(instance: BaseIndexerDefinition) -> tuple[int, str]:
            idx = instance.id.lower()
            if idx == "ncore":
                return (0, "")
            if idx == "bithumen":
                return (1, "")
            return (2, instance.name.lower())

        instances = self._definitions.values()
        if not include_disabled:
            instances = [inst for inst in instances if not inst.disabled]
        return sorted(instances, key=get_sort_key)

    def get_by_id(
        self, indexer_id: str, include_disabled: bool = False
    ) -> BaseIndexerDefinition:
        adapter = self._definitions.get(indexer_id)

        if not adapter or (not include_disabled and adapter.disabled):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nem regisztrált vagy letiltott indexer definition: {indexer_id}",
            )

        return adapter

    async def close_all(self) -> None:
        try:
            for adapter in self._definitions.values():
                await adapter.close()
        except Exception:
            logger.exception("Hiba történt az indexer definíciók leállításakor.")

    def sync_to_db(
        self,
        db: Session,
    ):
        discovered_definitions = self.get_list(include_disabled=True)

        discovered_ids = {instance.id for instance in discovered_definitions}

        to_delete = (
            db.query(IndexerDefinitionModel)
            .filter(IndexerDefinitionModel.id.not_in(discovered_ids))
            .all()
        )
        deleted_count = len(to_delete)
        for definition in to_delete:
            db.delete(definition)

        if deleted_count > 0:
            logger.info(
                f"🗑️ Törölve {deleted_count} elavult indexer definíció a DB-ből."
            )

        # Meglévő rekordok lekérése egyetlen lekérdezéssel
        db_definitions_map = {
            db_def.id: db_def for db_def in db.query(IndexerDefinitionModel).all()
        }

        fields = [
            "name",
            "url",
            "details_path",
            "requires_full_download",
            "order",
            "disabled",
        ]
        for index, instance in enumerate(discovered_definitions):
            instance_data = {
                "name": instance.name,
                "url": instance.url,
                "details_path": instance.details_path,
                "requires_full_download": instance.requires_full_download,
                "disabled": instance.disabled,
                "order": index,
            }

            if instance.id in db_definitions_map:
                db_definition = db_definitions_map[instance.id]

                if pydash.pick(db_definition, *fields) != instance_data:
                    for field in fields:
                        setattr(db_definition, field, instance_data[field])
            else:
                new_definition = IndexerDefinitionModel(
                    id=instance.id,
                    preference_id=PreferenceKey.SITE,
                    **instance_data,
                )
                db.add(new_definition)
