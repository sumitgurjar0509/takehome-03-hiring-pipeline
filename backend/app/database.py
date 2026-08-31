"""
SQLAlchemy engine and session setup. Sync engine (not async) — see
docs/decisions.md for why: this is a small internal tool, and a sync
session is far easier to reason about and explain than juggling async
sessions, and FastAPI runs sync route functions in a threadpool anyway.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
