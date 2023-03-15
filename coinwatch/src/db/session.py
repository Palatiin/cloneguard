# session.py

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from coinwatch import settings
from coinwatch.src.db import Base


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
    def __enter__(self):
        db_engine.execute("drop schema if exists public cascade")
        db_engine.execute("create schema public")
        db_engine.execute("grant all on schema public to postgres")
        Base.metadata.create_all(db_engine)

    def __exit__(self, exc_type, exc_val, exc_tb):
        db_session.close_all()


class DBSession:
    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        db_session.close_all()
