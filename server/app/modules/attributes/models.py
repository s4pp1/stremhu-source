import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.preferences.models import PreferenceModel


class AttributeModel(Base):
    __tablename__ = "attributes"
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "base",
    }

    id: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
    )

    type: Mapped[str] = mapped_column(
        sa.String,
        init=False,
    )

    order: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
    )

    preference_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("preferences.id", ondelete="CASCADE"),
        default=None,
    )

    preference: Mapped["PreferenceModel | None"] = relationship(
        "PreferenceModel",
        back_populates="attributes",
        init=False,
    )
