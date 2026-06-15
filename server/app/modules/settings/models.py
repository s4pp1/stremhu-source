import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class SettingModel(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(sa.String, primary_key=True)
    value: Mapped[dict] = mapped_column(sa.JSON, default_factory=dict)
