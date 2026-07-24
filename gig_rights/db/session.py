"""Database engine and session configuration using SQLAlchemy 2.0."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default SQLite database file; easily swapped for PostgreSQL in production
DATABASE_URL = "sqlite:///./gig_rights.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite concurrency
    echo=False,  # Set True to output raw SQL during debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""


def get_db():
    """FastAPI dependency yielding a thread-safe database session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
