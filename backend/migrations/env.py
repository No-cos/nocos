# migrations/env.py
# Alembic environment configuration for Nocos.
# Reads the database URL from config.py (which reads from .env) so that
# no credentials ever appear in this file or in alembic.ini.
# Imports all models via models.base so autogenerate detects every table.

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the backend directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config as app_config
from models.base import Base

# Import all models here so their tables are registered on Base.metadata.
# Alembic autogenerate compares Base.metadata against the live DB schema —
# any model not imported here will appear as a "drop table" in new migrations.
from models.project import Project      # noqa: F401
from models.task import Task            # noqa: F401
from models.subscriber import Subscriber  # noqa: F401

# Alembic Config object — provides access to values in alembic.ini
alembic_config = context.config

# Interpret the config file for Python logging
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Use our app's Base.metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """
    Return the database URL from the application config.

    Using the central config module ensures the URL is read consistently
    across the app and never hardcoded or duplicated.
    """
    return app_config.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generates SQL without a live DB connection).

    Useful for reviewing migration SQL before applying it in production.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (applies to a live database connection).

    This is the mode used during normal `alembic upgrade head` runs.
    """
    configuration = alembic_config.get_section(alembic_config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
