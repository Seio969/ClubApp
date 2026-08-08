import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from config import DATABASE_URL

# Verbose SQL logging is expensive (every statement gets formatted and
# written) and was previously hardcoded on; opt in with CLUBAPP_DB_ECHO=1
# when debugging instead of paying that cost on every run.
_ECHO = os.environ.get("CLUBAPP_DB_ECHO", "").strip().lower() in ("1", "true", "yes")

# Engine and session factory
engine = create_engine(DATABASE_URL, echo=_ECHO, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """Apply per-connection SQLite settings the engine itself can't set.

    journal_mode=WAL + synchronous=NORMAL lets reads (the table/view
    browser) proceed without blocking behind an in-progress write, instead
    of SQLite's default rollback-journal exclusive lock.

    Deliberately NOT setting foreign_keys=ON here: SQLite requires an FK's
    target column to be a PRIMARY KEY or UNIQUE, but Transaccion/SaldoSocios
    reference Socio.numero_socio, which is intentionally non-unique (shared
    family identifier - see the comment on that column in models.py).
    Enabling FK enforcement makes SQLite reject that relationship as a
    schema-level "foreign key mismatch" on every write to those tables and
    even on deleting a Socio - confirmed by testing before this comment was
    written. Revisit only alongside a redesign of that relationship.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session():
    """Yield a Session that commits on success and rolls back on error.

    Centralizes the open/commit-or-rollback/close lifecycle so write paths
    don't each hand-roll their own try/except/finally around SessionLocal().
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
