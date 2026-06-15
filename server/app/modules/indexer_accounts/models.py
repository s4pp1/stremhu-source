import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.indexer_definitions.models import IndexerDefinitionModel

if TYPE_CHECKING:
    from app.modules.torrents.models import TorrentModel


class IndexerAccountModel(Base):
    __tablename__ = "indexer_accounts"

    indexer_id: Mapped[str] = mapped_column(
        sa.ForeignKey("indexer_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    indexer_definition: Mapped[IndexerDefinitionModel] = relationship(
        "IndexerDefinitionModel",
        init=False,
    )

    username: Mapped[str] = mapped_column(sa.String)

    password: Mapped[str] = mapped_column(sa.String)

    hit_and_run: Mapped[bool | None] = mapped_column(sa.Boolean, default=None)

    keep_seed_seconds: Mapped[int | None] = mapped_column(sa.Integer, default=None)

    download_full_torrent: Mapped[bool] = mapped_column(sa.Boolean, default=False)

    cookies: Mapped[dict | None] = mapped_column(sa.JSON, default=None)

    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
    )

    torrents: Mapped[list["TorrentModel"]] = relationship(
        "TorrentModel",
        back_populates="indexer_account",
        init=False,
    )
