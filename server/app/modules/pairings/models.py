import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.modules.users.models import UserModel


class PairingModel(Base):
    __tablename__ = "pairings"

    expires_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
    )

    user_code: Mapped[str] = mapped_column(
        sa.String,
        index=True,
    )

    device_code: Mapped[str] = mapped_column(
        sa.String,
        index=True,
    )

    id: Mapped[str] = mapped_column(
        sa.String,
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    status: Mapped[str] = mapped_column(
        sa.String,
        default="pending",
    )

    user_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        default=None,
    )

    user: Mapped["UserModel | None"] = relationship(
        "UserModel",
        uselist=False,
        init=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default_factory=datetime.datetime.now,
        server_default=sa.func.now(),
        nullable=False,
    )
