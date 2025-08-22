from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    database_url = os.getenv(
        "DATABASE_URL",
        # Default matches docker-compose Postgres service
        "postgresql+psycopg://jobtracker:jobtracker@db:5432/jobtracker",
    )
    return database_url


engine = create_engine(get_database_url(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()


