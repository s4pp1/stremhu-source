import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String)
