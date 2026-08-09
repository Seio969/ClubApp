"""Database reset service (PLAN.md 2.15).

Two distinct operations, both deliberately hard to trigger by accident -
the UI layer (reset_view.py) gates each behind typing an exact
confirmation phrase plus a final Yes/No prompt, never a single
dismissable dialog:

- full_reset(): wipes every table and re-seeds the fixed metodos_pago
  rows - "start over" for the whole club database.
- scoped_reset(): clears only transacciones/saldos_socios/periodo,
  leaving socios, metodos_pago and reglas_cobro untouched - for
  discarding a season's financial activity while keeping membership and
  configuration.

Neither ever touches data/club_manager.db as a file (no os.remove) - both
use SQLAlchemy's drop_all/create_all or row-level deletes against the
existing engine, which sidesteps file-locking/WAL concerns entirely.
"""

from __future__ import annotations

from database.audit import record_log
from database.models import Base, Periodo, SaldoSocios, Transaccion
from database.seed_db import seed_all
from database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)


class ResetService:
    def full_reset(self) -> bool:
        """Drop and recreate every table, then re-seed metodos_pago.

        Imports `engine` from database.session at call time (not at
        module import time) so this - like every other write path here -
        respects whatever engine is bound at the moment it runs; tests
        monkeypatch database.session.engine per-test, and a module-level
        import would have captured the real engine before that patch
        applied (see tests/conftest.py's note on this exact gotcha).
        """
        try:
            from database.session import engine

            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            seed_all()
            with get_session() as session:
                record_log(
                    session,
                    id_socio=None,
                    accion="reset_completo",
                    tabla_afectada="*",
                    id_registro_afectado=None,
                    descripcion_cambio=(
                        "Reinicio completo de la base de datos: todas las tablas vaciadas "
                        "y métodos de pago fijos re-sembrados."
                    ),
                )
            logger.info("ResetService.full_reset: database fully reset and re-seeded")
            return True
        except Exception as exc:
            logger.exception("ResetService.full_reset: failed - %s", exc)
            return False

    def scoped_reset(self) -> bool:
        """Clear transacciones/saldos_socios/periodo only.

        Socios, metodos_pago, reglas_cobro and the existing logs are left
        untouched - this is "discard financial activity", not "start
        over".
        """
        try:
            with get_session() as session:
                session.query(Transaccion).delete()
                session.query(SaldoSocios).delete()
                session.query(Periodo).delete()
                record_log(
                    session,
                    id_socio=None,
                    accion="reset_parcial",
                    tabla_afectada="transacciones,saldos_socios,periodo",
                    id_registro_afectado=None,
                    descripcion_cambio=(
                        "Reinicio parcial: transacciones, saldos y periodos eliminados; "
                        "socios y configuración (métodos de pago, reglas de cobro) conservados."
                    ),
                )
            logger.info("ResetService.scoped_reset: transacciones/saldos_socios/periodo cleared")
            return True
        except Exception as exc:
            logger.exception("ResetService.scoped_reset: failed - %s", exc)
            return False
