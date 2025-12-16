import asyncio
import os
import sys
from logging.config import fileConfig

# Add the project root to the python path so we can import 'app'
# Assuming env.py is in backend/alembic/
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override the sqlalchemy.url in alembic.ini with the one from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True, # Critical for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        render_as_batch=True # Critical for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    engine_kwargs = {}
    if settings.DATABASE_URL.startswith("postgresql"):
        engine_kwargs["connect_args"] = {"connect_timeout": 10}

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        **engine_kwargs,
    )

    last_error: Exception | None = None
    for attempt in range(1, 11):
        try:
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
            last_error = None
            break
        except OperationalError as exc:
            last_error = exc
            if attempt >= 10:
                break
            delay_s = min(2 ** (attempt - 1), 10)
            print(
                "Database connection failed during migrations "
                f"(attempt {attempt}/10). Retrying in {delay_s}s...",
                flush=True,
            )
            await asyncio.sleep(delay_s)

    await connectable.dispose()
    if last_error is not None:
        raise last_error

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
