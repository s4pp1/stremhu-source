import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.attributes.models import AttributeModel
from app.modules.preferences.models import PreferenceModel


class PreferenceDefinitionModel(Base):
    """
    Stores a configured preference definition (a named group of prioritised
    attribute choices).  One definition can be shared by a system-level or
    user-level preference record.
    """

    __tablename__ = "preference_definitions"

    preference_id: Mapped[str] = mapped_column(
        sa.ForeignKey("preferences.id", ondelete="CASCADE"),
    )

    preference: Mapped["PreferenceModel"] = relationship(
        "PreferenceModel",
        init=False,
    )

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    definition_attributes: Mapped[list["PreferenceDefinitionAttributeModel"]] = (
        relationship(
            "PreferenceDefinitionAttributeModel",
            back_populates="definition",
            cascade="all, delete-orphan",
            order_by="PreferenceDefinitionAttributeModel.order",
            init=False,
        )
    )


class PreferenceDefinitionAttributeModel(Base):
    """Links a preference definition to an ordered list of attribute choices."""

    __tablename__ = "preference_definition_attributes"

    definition_id: Mapped[str] = mapped_column(
        sa.ForeignKey("preference_definitions.id", ondelete="CASCADE"),
    )

    attribute_id: Mapped[str] = mapped_column(
        sa.ForeignKey("attributes.id", ondelete="CASCADE"),
    )

    order: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    definition: Mapped["PreferenceDefinitionModel"] = relationship(
        "PreferenceDefinitionModel",
        back_populates="definition_attributes",
        init=False,
    )

    attribute: Mapped["AttributeModel"] = relationship(
        "AttributeModel",
        uselist=False,
        init=False,
    )
