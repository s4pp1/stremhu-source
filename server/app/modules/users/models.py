import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base, UTCDateTime
from app.modules.attribute_exclusions.models import AttributeExclusionModel
from app.modules.roles.constants import UserRoleKey
from app.modules.roles.models import RoleModel
from app.modules.user_preference_definitions.models import UserPreferenceDefinitionModel


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

    only_best_torrent: Mapped[bool] = mapped_column(
        default=False,
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
