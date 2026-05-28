import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from common.database import Base
from modules.preferences.enums import PreferenceEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from modules.attributes.models import AttributeModel
    from modules.users.models import UserModel


# ─── Kategória törzsadatok ────────────────────────────────────────────────────


class PreferenceModel(Base):
    """A preference category record (e.g. 'resolution', 'language')."""

    __tablename__ = "preferences"

    id: Mapped[PreferenceEnum] = mapped_column(sa.String, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String)
    description: Mapped[str] = mapped_column(sa.String)


# ─── Preferencia Definíció ────────────────────────────────────────────────────


class PreferenceDefinitionModel(Base):
    """
    Stores a configured preference definition (a named group of prioritised
    attribute choices).  One definition can be shared by a system-level or
    user-level preference record.
    """

    __tablename__ = "preference_definitions"

    preference_id: Mapped[PreferenceEnum] = mapped_column(
        ForeignKey("preferences.id", ondelete="CASCADE"),
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


# ─── Definíció <-> Attribútum kapcsolótábla ───────────────────────────────────


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


# ─── Rendszer szintű preferencia ─────────────────────────────────────────────


class SystemPreferenceModel(Base):
    """Global default priority orders for preference categories."""

    __tablename__ = "system_preferences"

    definition_id: Mapped[str] = mapped_column(
        ForeignKey("preference_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    order: Mapped[int] = mapped_column(Integer, nullable=False)

    definition: Mapped["PreferenceDefinitionModel"] = relationship(
        "PreferenceDefinitionModel",
        cascade="all, delete-orphan",
        single_parent=True,
        init=False,
    )


# ─── Felhasználó szintű preferencia ──────────────────────────────────────────


class UserPreferenceModel(Base):
    """
    User preference overrides representing the category priority order.
    Individual choices (preferred/blocked values) live in the
    preference_definition_attributes table via the linked definition.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    definition_id: Mapped[str] = mapped_column(
        ForeignKey("preference_definitions.id", ondelete="CASCADE"),
    )

    order: Mapped[int] = mapped_column(Integer)

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="preferences",
        init=False,
    )

    definition: Mapped["PreferenceDefinitionModel"] = relationship(
        "PreferenceDefinitionModel",
        cascade="all, delete-orphan",
        single_parent=True,
        init=False,
    )
