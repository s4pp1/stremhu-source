from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.common.schemas.internal import ImdbInfo
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.playback_histories.schemas.internal import (
    PlaybackHistoryClientInfo,
)

if TYPE_CHECKING:
    from app.modules.users.models import UserModel


class PlaybackHistoryModel(Base):
    __tablename__ = "playback_histories"
    __table_args__ = (
        sa.Index(
            "ix_playback_history_indexer_torrent",
            "indexer_id",
            "torrent_id",
        ),
    )

    playback_id: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        init=False,
    )

    indexer_id: Mapped[str] = mapped_column(
        sa.ForeignKey(
            "indexer_definitions.id",
            ondelete="CASCADE",
        ),
    )

    indexer_definition: Mapped["IndexerDefinitionModel"] = relationship(
        "IndexerDefinitionModel",
        init=False,
    )

    torrent_id: Mapped[str] = mapped_column(sa.String)

    file_index: Mapped[int] = mapped_column(sa.Integer)

    torrent_name: Mapped[str] = mapped_column(sa.String)

    file_name: Mapped[str] = mapped_column(sa.String)

    imdb_info: Mapped[dict | None] = mapped_column(sa.JSON)

    client: Mapped[dict | None] = mapped_column(sa.JSON)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.now,
        index=True,
    )

    @property
    def imdb_info_typed(self) -> ImdbInfo | None:
        if not self.imdb_info:
            return None
        return ImdbInfo.model_validate(self.imdb_info)

    @imdb_info_typed.setter
    def imdb_info_typed(self, value: ImdbInfo | None) -> None:
        self.imdb_info = value.model_dump() if value else None

    @property
    def client_typed(self) -> PlaybackHistoryClientInfo | None:
        if not self.client:
            return None
        return PlaybackHistoryClientInfo.model_validate(self.client)

    @client_typed.setter
    def client_typed(self, value: PlaybackHistoryClientInfo | None) -> None:
        self.client = value.model_dump() if value else None
