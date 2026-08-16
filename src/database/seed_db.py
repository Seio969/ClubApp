from database.session import get_session
from database.models import MetodoPago, ReglaCobro
from utils.logger import get_logger

logger = get_logger(__name__)

# Fixed payment methods from README.md's "Formas de Pago" section.
METODOS_PAGO_FIJOS = [
    "REMESA",
    "EFECTIVO",
    "TRANSFERENCIA",
    "TRANSFERENCIA/EFECTIVO",
    "INACTIVO",
]

# The club's one standing billing rule, entered by hand in the current DB.
# Unlike METODOS_PAGO_FIJOS this isn't a closed/protected set (reglas_cobro
# has no fixed set - see CLAUDE.md), just a starting row so a fresh DB isn't
# empty; users can still add/edit/deactivate rules freely afterwards.
REGLAS_COBRO_INICIALES = [
    {
        "descripcion": "Cuota mensual estándar",
        "cuota_mensual": 36.00,
        "plazo_pago": None,
        "penalizacion": 3.60,
        "descuento": None,
        "estado": "activo",
    },
]


def seed_metodos_pago() -> int:
    """Insert any of the fixed payment methods missing from metodos_pago.

    Idempotent: only inserts names not already present, so it's safe to
    call on every startup/init, not just once on a fresh DB.
    Returns the number of rows inserted.
    """
    inserted = 0
    with get_session() as session:
        existing = {row.nombre for row in session.query(MetodoPago.nombre).all()}
        for nombre in METODOS_PAGO_FIJOS:
            if nombre not in existing:
                session.add(MetodoPago(nombre=nombre))
                inserted += 1
    if inserted:
        logger.info("Seeded %d metodos_pago row(s).", inserted)
    return inserted


def seed_reglas_cobro() -> int:
    """Insert any starting reglas_cobro rows missing (matched by descripcion).

    Idempotent: only inserts descripciones not already present, so it's safe
    to call on every startup/init, not just once on a fresh DB.
    Returns the number of rows inserted.
    """
    inserted = 0
    with get_session() as session:
        existing = {row.descripcion for row in session.query(ReglaCobro.descripcion).all()}
        for regla in REGLAS_COBRO_INICIALES:
            if regla["descripcion"] not in existing:
                session.add(ReglaCobro(**regla))
                inserted += 1
    if inserted:
        logger.info("Seeded %d reglas_cobro row(s).", inserted)
    return inserted


def seed_all() -> None:
    seed_metodos_pago()
    seed_reglas_cobro()


if __name__ == "__main__":
    seed_all()
