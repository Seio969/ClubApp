from database.session import get_session
from database.models import MetodoPago
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


def seed_all() -> None:
    seed_metodos_pago()


if __name__ == "__main__":
    seed_all()
