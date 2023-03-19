# session.py

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from coinwatch import settings
from coinwatch.src.db.schema import Base

logger = structlog.get_logger(__name__)


def create_db() -> (Engine, scoped_session, DeclarativeMeta):
    db_engine = create_engine(
        f"postgresql://{settings.PG_USER}:{settings.PG_PASS}@{settings.PG_HOST}:{settings.PG_PORT}/{settings.DB_NAME}",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=db_engine))
    Base = declarative_base()
    Base.query = db_session.query_property()

    return db_engine, db_session


db_engine, db_session = create_db()


class DBSchemaSetup:
    """Reinitialize DB, only for local testing development."""

    def __enter__(self):
        with db_engine.connect() as connection:
            with connection.begin():
                connection.execute(text("drop schema if exists public cascade"))
                connection.execute(text("create schema public"))
                connection.execute(text("grant all on schema public to admin"))
                Base.metadata.create_all(connection)

    def __exit__(self, exc_type, exc_val, exc_tb):
        db_session.close_all()


class DBSession:
    """DB session wrapper, automatically closes connection to DB."""

    def __enter__(self):
        logger.info("DB session enter.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        db_session.close_all()
        logger.info("Close DB session.")
