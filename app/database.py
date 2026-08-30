"""SQLAlchemy engine/session setup, shared by every table in app/models.py.

Two ways code elsewhere gets a database session:
  - FastAPI routes use `Depends(get_db)` (see any admin router for
    examples) — FastAPI calls get_db(), hands the route the yielded
    session, and closes it afterwards no matter what happens.
  - app/content.py (read-only, used by the public pages) instead does
    `with SessionLocal() as db:` directly, since it's not running inside
    a FastAPI dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# Railway (and most managed Postgres hosts) hand out a "postgres://" URL;
# point SQLAlchemy at the psycopg (v3) driver explicitly.
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLite's default driver only allows a connection to be used from the
# thread that created it; FastAPI can hand a request to a different
# thread, so this relaxes that check. Not needed (and not passed) for
# Postgres, which doesn't have this restriction.
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
# Managed Postgres hosts (Railway included) silently close connections
# that sit idle for a while. Without pool_pre_ping, the next request to
# reuse one of those dead connections fails with a confusing
# "SSL connection has been closed unexpectedly" error. pool_pre_ping runs
# a cheap SELECT 1 before handing out a pooled connection and transparently
# reconnects if it's gone — doesn't apply to (and isn't needed for) SQLite.
engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=not database_url.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Every table in app/models.py inherits from this. SQLAlchemy uses it
    to know which classes are tables when app/main.py calls
    Base.metadata.create_all(engine) at startup."""

    pass


def get_db():
    """FastAPI dependency that hands a route a database session and
    guarantees it gets closed afterwards, even if the route raises.
    Usage: `db: Session = Depends(get_db)` as a route parameter."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
