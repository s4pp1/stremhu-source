import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.preference_definitions.models import PreferenceDefinitionModel

if TYPE_CHECKING:
    from app.modules.users.models import UserModel


class UserPreferenceDefinitionModel(Base):
    """
    User preference overrides representing the category priority order.
    Individual choices (preferred/blocked values) live in the
    preference_definition_attributes table via the linked definition.
    """

    __tablename__ = "user_preference_definitions"

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
    )

    definition_id: Mapped[str] = mapped_column(
        sa.ForeignKey("preference_definitions.id", ondelete="CASCADE"),
    )

    order: Mapped[int] = mapped_column(sa.Integer)

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="preference_definitions",
        init=False,
    )

    definition: Mapped["PreferenceDefinitionModel"] = relationship(
        "PreferenceDefinitionModel",
        cascade="all, delete-orphan",
        single_parent=True,
        init=False,
    )
