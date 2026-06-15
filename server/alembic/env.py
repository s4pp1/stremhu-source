import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Any, Literal

from app.common.database import Base, UTCDateTime, engine
from app.config import config


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    """Alembic hook: UTCDateTime-t sa.DateTime()-ként rendereli, mert a séma szintű típus azonos."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine

    with connectable.connect() as connection:
        if connectable.dialect.name == "sqlite":
            raw_connection = connection.connection.dbapi_connection
            if raw_connection is not None:
                cursor = raw_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=OFF")
                cursor.close()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
