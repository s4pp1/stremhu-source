from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base

if TYPE_CHECKING:
    from app.modules.attributes.models import AttributeModel


class PreferenceModel(Base):
    __tablename__ = "preferences"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)

    name: Mapped[str] = mapped_column(sa.String)

    description: Mapped[str] = mapped_column(sa.String)

    multiple: Mapped[bool] = mapped_column(sa.Boolean, default=False)

    order: Mapped[int] = mapped_column(sa.Integer, default=0)

    emoji: Mapped[str | None] = mapped_column(sa.String, default=None)

    attributes: Mapped[list["AttributeModel"]] = relationship(
        "AttributeModel",
        back_populates="preference",
        init=False,
        order_by="AttributeModel.order",
    )
