import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.preference_definitions.models import PreferenceDefinitionModel


class SystemPreferenceDefinitionModel(Base):
    """Global default priority orders for preference categories."""

    __tablename__ = "system_preference_definitions"

    definition_id: Mapped[str] = mapped_column(
        sa.ForeignKey("preference_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    order: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    definition: Mapped["PreferenceDefinitionModel"] = relationship(
        "PreferenceDefinitionModel",
        cascade="all, delete-orphan",
        single_parent=True,
        init=False,
    )
