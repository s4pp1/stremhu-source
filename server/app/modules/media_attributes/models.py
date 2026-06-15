import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.attributes.models import AttributeModel


class MediaAttributeModel(AttributeModel, kw_only=True):
    __tablename__ = "media_attributes"
    __mapper_args__ = {
        "polymorphic_identity": "media",
    }

    name: Mapped[str] = mapped_column(sa.String)

    short_name: Mapped[str | None] = mapped_column(
        sa.String,
        default=None,
    )

    description: Mapped[str | None] = mapped_column(
        sa.String,
        default=None,
    )

    id: Mapped[str] = mapped_column(
        sa.ForeignKey("attributes.id", ondelete="CASCADE"), primary_key=True
    )

    pattern: Mapped[str | None] = mapped_column(
        sa.String,
        default=None,
    )

    is_preferable: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
    )

    show_in_details: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
    )
