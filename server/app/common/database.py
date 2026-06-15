import importlib
import zoneinfo
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import tzlocal
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Session, sessionmaker
from sqlalchemy.types import DateTime, TypeDecorator

from app.config import config

# Naming convention is CRITICAL for SQLite migrations in Alembic
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    SERVER_TZ = zoneinfo.ZoneInfo(tzlocal.get_localzone_name())

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            if value.tzinfo is not None:
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                local_dt = value.replace(tzinfo=self.SERVER_TZ)
                return local_dt.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            utc_dt = value.replace(tzinfo=timezone.utc)
            return utc_dt.astimezone(self.SERVER_TZ)
        return value


class Base(
    MappedAsDataclass,
    DeclarativeBase,
    kw_only=True,
):
    metadata = MetaData(naming_convention=convention)
    type_annotation_map = {
        datetime: UTCDateTime,
    }


connect_args = {"check_same_thread": False}
engine = create_engine(config.database_url, connect_args=connect_args)


# Biztosítjuk a Foreign Key megszorítások, a WAL mód és a szinkronizáció beállítását minden SQLite kapcsolatnál
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Standard Python környezetkezelő (Context Manager) adatbázis tranzakciókhoz.
    Automatikusan kezeli a commit, rollback és close életciklusokat.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI specifikus függőség-injektor generátor.
    A háttérben biztonságosan delegál a db_session környezetkezelőnek.
    """
    with db_session() as db:
        yield db


root_path = Path(__file__).resolve().parent.parent
for path in root_path.rglob("models.py"):
    relative_path = path.relative_to(root_path)
    module_name = "app." + ".".join(relative_path.with_suffix("").parts)
    try:
        importlib.import_module(module_name)
    except Exception:
        pass
