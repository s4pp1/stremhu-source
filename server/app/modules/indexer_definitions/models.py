import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.attributes.models import AttributeModel


class IndexerDefinitionModel(AttributeModel, kw_only=True):
    __tablename__ = "indexer_definitions"
    __mapper_args__ = {
        "polymorphic_identity": "indexer_definition",
    }

    id: Mapped[str] = mapped_column(
        sa.ForeignKey("attributes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        sa.String,
    )

    url: Mapped[str] = mapped_column(
        sa.String,
    )

    details_path: Mapped[str] = mapped_column(
        sa.String,
    )

    requires_full_download: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
    )

    disabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
    )
