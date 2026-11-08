import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexer_definitions.schemas.internal import IndexerDefinition


class IndexerDefinitionRef(BaseModel):
    """Session nélküli, megosztható indexer-definíció; az ORM-modell olvasott mezőit hordozza."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    url: str
    details_path: str
    requires_full_download: bool
    supports_totp: bool
    disabled: bool
    order: int
    preference_id: str | None = None

    @classmethod
    def from_model(cls, model: IndexerDefinitionModel) -> "IndexerDefinitionRef":
        return cls(
            id=model.id,
            name=model.name,
            url=model.url,
            details_path=model.details_path,
            requires_full_download=model.requires_full_download,
            supports_totp=model.supports_totp,
            disabled=model.disabled,
            order=model.order,
            preference_id=model.preference_id,
        )


class IndexerAccountRef(BaseModel):
    """Session nélküli account-hivatkozás keresési eredményhez; hitelesítő adatot nem tartalmaz."""

    model_config = ConfigDict(frozen=True)

    indexer_id: str
    indexer_definition: IndexerDefinitionRef
    download_full_torrent: bool = False

    @classmethod
    def from_model(cls, model: IndexerAccountModel) -> "IndexerAccountRef":
        return cls(
            indexer_id=model.indexer_id,
            download_full_torrent=bool(model.download_full_torrent),
            indexer_definition=IndexerDefinitionRef.from_model(
                model.indexer_definition
            ),
        )


class IndexerAccountBase(BaseModel):
    username: str
    download_full_torrent: bool
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None


class IndexerAccountCreate(IndexerAccountBase):
    indexer_id: str
    password: str
    totp_secret: str | None = None
    cookies: dict[str, str] | None = None


class IndexerAccount(IndexerAccountBase):
    indexer_definition: IndexerDefinition
    updated_at: datetime.datetime
    created_at: datetime.datetime


class IndexerAccountUpdate(BaseModel):
    download_full_torrent: bool | None = None
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
