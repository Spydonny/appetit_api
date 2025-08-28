from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _build_engine():
    url = settings.DATABASE_URL
    engine_kwargs = {
        "echo": (settings.APP_ENV == "dev"),
        "pool_pre_ping": True,
        "future": True,
    }

    if url.startswith("sqlite"):
        raise RuntimeError("SQLite is not supported. Please configure PostgreSQL via DATABASE_URL or DB_* settings.")

    # postgreSQL specific config with secure connection pooling
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_CONNECTION_TIMEOUT,
        "pool_recycle": 3600,  # Recycle connections every hour
        "pool_reset_on_return": "commit",  # Reset connections on return
        "connect_args": {
            "connect_timeout": settings.DB_CONNECTION_TIMEOUT,
            "application_name": "appetit_backend",
        }
    })

    return create_engine(url, **engine_kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# fastAPI dependency
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def session_scope() -> Iterator["Session"]:
    """provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator["Session"]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()