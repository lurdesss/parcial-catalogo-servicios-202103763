import os

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registra las tablas)
from app.config import _url
from app.extensions import db

config = context.config
target_metadata = db.metadata


def _database_url():
    return config.get_main_option("sqlalchemy.url") or _url(os.environ["DATABASE_URL"])


def run_migrations_online():
    engine = create_engine(_database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
