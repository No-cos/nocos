# db.py
# Database engine and session factory for the Nocos backend.
# Centralised here so routers, the sync job, and tests all import from
# one place — prevents multiple engines being created accidentally.

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from config import config

logger = logging.getLogger(__name__)

# pool_pre_ping=True silently reconnects on stale connections after a DB restart
# without this, long-lived workers get "server closed the connection" errors.
engine = create_engine(
    config.DATABASE_URL or "sqlite:///:memory:",
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a database session per request.

    Usage in a router:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The session is closed in the finally block so connections return to
    the pool regardless of whether the handler raised an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
