from sqlalchemy import text

from database.session import engine
from database.models import Base
from database.seed_db import seed_all
from utils.logger import get_logger
logger = get_logger(__name__)


def _add_missing_columns() -> None:
    """Patch columns added to models.py after a DB already exists.

    create_all() only creates missing tables, never alters existing ones
    (see CLAUDE.md's note on this), so a column added to an existing model
    - like MetodoPago.estado - would otherwise silently never appear on a
    DB created before that change. There's no Alembic in this project yet
    (PLAN.md 2.14, deliberately deferred), so this is a minimal stopgap:
    check via PRAGMA table_info and ALTER TABLE ADD COLUMN only if missing.
    Safe to call on every startup - a no-op once the column exists.
    """
    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(metodos_pago)"))}
        if columns and "estado" not in columns:
            conn.execute(text("ALTER TABLE metodos_pago ADD COLUMN estado VARCHAR DEFAULT 'activo'"))
            conn.commit()
            logger.info("Migrated metodos_pago: added missing 'estado' column.")


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    seed_all()
    logger.info("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
