from sqlalchemy import text

from database.session import engine
from database.models import Base
from database.seed_db import seed_all
from utils.logger import get_logger
logger = get_logger(__name__)


# (table, column, ALTER TABLE ADD COLUMN ddl) for every column added to
# models.py after a DB already existed - see _add_missing_columns.
_COLUMN_MIGRATIONS = [
    ("metodos_pago", "estado", "ALTER TABLE metodos_pago ADD COLUMN estado VARCHAR DEFAULT 'activo'"),
    ("reglas_cobro", "estado", "ALTER TABLE reglas_cobro ADD COLUMN estado VARCHAR DEFAULT 'activo'"),
]


def _add_missing_columns() -> None:
    """Patch columns added to models.py after a DB already exists.

    create_all() only creates missing tables, never alters existing ones
    (see CLAUDE.md's note on this), so a column added to an existing model
    - like MetodoPago.estado - would otherwise silently never appear on a
    DB created before that change. There's no Alembic in this project yet
    (PLAN.md 2.14, deliberately deferred), so this is a minimal stopgap:
    check via PRAGMA table_info and ALTER TABLE ADD COLUMN only if missing.
    Safe to call on every startup - a no-op once every column exists.
    """
    with engine.connect() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            columns = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if columns and column not in columns:
                conn.execute(text(ddl))
                conn.commit()
                logger.info("Migrated %s: added missing '%s' column.", table, column)


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    seed_all()
    logger.info("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
