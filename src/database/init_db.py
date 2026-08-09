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
    ("socios", "es_titular", "ALTER TABLE socios ADD COLUMN es_titular BOOLEAN DEFAULT 0"),
]

# lowercase/legacy transacciones.tipo value -> canonical TIPOS_TRANSACCION
# value (features/transactions/service.py) - see _normalize_tipo_transaccion.
_TIPO_CANONICAL = {
    "cargo": "Cargo",
    "pago": "Pago",
    "reembolso": "Reembolso",
    "devolucion": "Devolución",
    "devolución": "Devolución",
}


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


def _normalize_tipo_transaccion() -> None:
    """Normalize transacciones.tipo to canonical Title Case.

    Older rows were written back when TIPOS_TRANSACCION was all-lowercase
    ("cargo"/"pago"/"reembolso"), and some were entered inconsistently
    outside the dialog's dropdown (e.g. a legacy import), leaving a mix of
    casings in the same column. The dropdown itself now only ever writes
    canonical values (see TIPOS_TRANSACCION), so this is a one-time-per-row
    cleanup of pre-existing data, not an ongoing need - safe to call on
    every startup, a no-op once every row already matches its canonical form.
    """
    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(transacciones)"))}
        if "tipo" not in columns:
            return
        for legacy, canonical in _TIPO_CANONICAL.items():
            result = conn.execute(
                text(
                    "UPDATE transacciones SET tipo = :canonical "
                    "WHERE LOWER(TRIM(tipo)) = :legacy AND tipo != :canonical"
                ),
                {"canonical": canonical, "legacy": legacy},
            )
            if result.rowcount:
                conn.commit()
                logger.info(
                    "Normalized %d transacciones.tipo row(s) '%s' -> '%s'.",
                    result.rowcount, legacy, canonical,
                )


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    _normalize_tipo_transaccion()
    seed_all()
    logger.info("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
