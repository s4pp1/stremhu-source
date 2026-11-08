import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base, UTCDateTime
from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.roles.constants import UserRoleKey
from app.modules.roles.models import RoleModel
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel

if TYPE_CHECKING:
    from app.modules.preferences.models import PreferenceModel


class UserModel(Base):
    __tablename__ = "users"

    preference_definitions: Mapped[list["UserPreferenceDefinitionModel"]] = (
        relationship(
            "UserPreferenceDefinitionModel",
            back_populates="user",
            cascade="all, delete-orphan",
            init=False,
        )
    )

    attribute_exclusions: Mapped[list["AttributeExclusionModel"]] = relationship(
        "AttributeExclusionModel",
        back_populates="user",
        cascade="all, delete-orphan",
        init=False,
    )

    username: Mapped[str] = mapped_column(
        sa.String,
        unique=True,
        index=True,
    )

    id: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    session_epoch: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))

    password_hash: Mapped[str | None] = mapped_column(
        sa.Text,
        default=None,
    )

    api_key: Mapped[str] = mapped_column(
        sa.String,
        default_factory=lambda: str(uuid.uuid4()),
        index=True,
    )

    role_id: Mapped[str] = mapped_column(
        sa.ForeignKey("roles.id"),
        default=UserRoleKey.USER,
    )

    role: Mapped["RoleModel"] = relationship("RoleModel", init=False)

    torrent_seed: Mapped[int | None] = mapped_column(
        default=None,
    )

    enable_smart_filter: Mapped[bool] = mapped_column(
        default=False,
    )

    enable_stream_deduplication: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        server_default=sa.text("1"),
    )

    smart_filter_grouping_preference_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("preferences.id", ondelete="SET NULL"),
        default=None,
    )

    smart_filter_grouping_preference: Mapped["PreferenceModel | None"] = relationship(
        "PreferenceModel",
        init=False,
    )

    smart_filter_limit: Mapped[int] = mapped_column(
        sa.Integer,
        default=1,
    )

    enable_fallback_subtitles: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
        server_default=sa.text("0"),
    )

    enable_catalog_search: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        server_default=sa.text("1"),
    )

    # A helyben már letöltött fájlok „⚡ Letöltve” jelölése és a lista elejére sorolása
    enable_downloaded_marker: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        server_default=sa.text("1"),
    )

    max_concurrent_streams: Mapped[int | None] = mapped_column(
        sa.Integer,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default_factory=datetime.now,
        server_default=sa.func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default_factory=datetime.now,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )
