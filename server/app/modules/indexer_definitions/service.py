import asyncio

import pydash
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.async_utils import await_owned_task
from app.common.commit_actions import mark_stream_cache_dirty
from app.common.logger import logger
from app.modules.indexer_definitions.base_indexer_definition import (
    BaseIndexerDefinition,
)
from app.modules.indexer_definitions.integrations import discover_indexer_definitions
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.protocols import IndexerAccountStorage
from app.modules.preference_definitions.dependencies import (
    create_preference_definitions_service,
)
from app.modules.preferences.constants import PreferenceKey


class IndexerDefinitionsService:
    def __init__(
        self,
        indexer_account_storage: IndexerAccountStorage | None = None,
    ):
        self._definitions: dict[str, BaseIndexerDefinition] = {}
        self._close_task: asyncio.Task[bool] | None = None

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

    def stop_admission(self) -> None:
        for adapter in self._definitions.values():
            adapter.stop_admission()

    async def close_logins(self) -> bool:
        complete = True
        for adapter in self._definitions.values():
            try:
                await adapter.close_logins()
            except (Exception, asyncio.CancelledError) as error:
                complete = False
                logger.error("Indexer login close failed: kind=%s", type(error).__name__)
        return complete

    async def _close_definitions(self) -> bool:
        complete = True
        for indexer_id, adapter in tuple(self._definitions.items()):
            try:
                await adapter.close()
            except (Exception, asyncio.CancelledError) as error:
                complete = False
                logger.error("Indexer close failed: provider=%s kind=%s", indexer_id, type(error).__name__)
        return complete

    async def close_all(self) -> bool:
        if getattr(self, "_close_task", None) is None:
            self._close_task = asyncio.create_task(self._close_definitions(), name="indexer-clients-close")
        assert self._close_task is not None
        return await await_owned_task(self._close_task)

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

        if deleted_count > 0:
            preference_definitions_service = create_preference_definitions_service(db)

            for definition in to_delete:
                preference_definitions_service.remove_attribute_from_all(definition.id)
                db.delete(definition)

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
            "supports_totp",
            "order",
            "disabled",
        ]
        for index, instance in enumerate(discovered_definitions):
            instance_data = {
                "name": instance.name,
                "url": instance.url,
                "details_path": instance.details_path,
                "requires_full_download": instance.requires_full_download,
                "supports_totp": instance.supports_totp,
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

        mark_stream_cache_dirty(db)
