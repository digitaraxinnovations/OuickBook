"""
Database engine and session.

`get_db` gives each API request its own session and always closes it.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.get_database_url(),
    echo=settings.database_echo,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Writes the audit log after every save (see db/audit.py).
import app.db.audit  # noqa: E402, F401
