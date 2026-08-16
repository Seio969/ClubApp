"""BalancesService: SaldoSocios.saldo_actual calculation and carry-over
(PLAN.md 2.5).

Formula (decided 2026-08-12, reembolso sign corrected 2026-08-12):
    saldo_actual = saldo_anterior + cargos - pagos + reembolsos + devoluciones

Reembolso and devolución both add back to what's owed (same direction as
cargo): a reembolso hands cash back to the socio, undoing part of a prior
pago's reduction, the same way a devolución (bounced pago) does - see
CLAUDE.md's balance formula note.

saldo_actual is a continuous running total, never reset per período:
saldo_anterior always chains forward from the immediately-preceding
período's saldo_actual for the same numero_socio (the family, not an
individual Socio row - see models.py's note on numero_socio).

recalcular_saldo is meant to be called from inside the same get_session()
block as the Transaccion write that triggered it (see
TransactionsService.add_transaction) so a rollback undoes the balance
update together with the transaction, the same pattern record_log()
already uses for audit rows.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from database.models import Periodo, SaldoSocios, Transaccion
from utils.logger import get_logger

logger = get_logger(__name__)


class BalancesService:
    """Recomputes SaldoSocios rows from Transaccion, the source of truth."""

    def recalcular_saldo(self, session: Session, numero_socio: Optional[str], id_periodo: Optional[int]) -> None:
        """Recompute numero_socio's SaldoSocios row for id_periodo, then
        cascade the resulting saldo_actual forward into any later período
        that already has a row for numero_socio, so the chain stays
        consistent even when a transaction is registered against a período
        that isn't the most recently touched one.

        No-ops on a missing numero_socio/id_periodo (callers may not always
        have both, e.g. incomplete data mid-validation) rather than raising.
        """
        if not numero_socio or id_periodo is None:
            return
        periodo = session.get(Periodo, id_periodo)
        if periodo is None:
            logger.warning("BalancesService.recalcular_saldo: unknown id_periodo=%s", id_periodo)
            return

        self._recalcular_uno(session, numero_socio, periodo)

        siguientes = (
            session.query(SaldoSocios)
            .join(Periodo, SaldoSocios.id_periodo == Periodo.id_periodo)
            .filter(
                SaldoSocios.numero_socio == numero_socio,
                Periodo.fecha_inicio > periodo.fecha_inicio,
            )
            .order_by(Periodo.fecha_inicio.asc())
            .all()
        )
        for saldo in siguientes:
            self._recalcular_uno(session, numero_socio, saldo.periodo)

    def _recalcular_uno(self, session: Session, numero_socio: str, periodo: Periodo) -> SaldoSocios:
        """Recompute (upsert) the single SaldoSocios row for numero_socio +
        periodo, pulling saldo_anterior from the immediately-preceding
        período (by fecha_inicio) that already has a row for numero_socio.
        """
        anterior = (
            session.query(SaldoSocios)
            .join(Periodo, SaldoSocios.id_periodo == Periodo.id_periodo)
            .filter(
                SaldoSocios.numero_socio == numero_socio,
                Periodo.fecha_inicio < periodo.fecha_inicio,
            )
            .order_by(Periodo.fecha_inicio.desc())
            .first()
        )
        saldo_anterior = anterior.saldo_actual if anterior else Decimal("0")

        cargos = self._sum_tipo(session, numero_socio, periodo.id_periodo, "Cargo")
        pagos = self._sum_tipo(session, numero_socio, periodo.id_periodo, "Pago")
        reembolsos = self._sum_tipo(session, numero_socio, periodo.id_periodo, "Reembolso")
        devoluciones = self._sum_tipo(session, numero_socio, periodo.id_periodo, "Devolución")
        saldo_actual = saldo_anterior + cargos - pagos + reembolsos + devoluciones

        saldo = (
            session.query(SaldoSocios)
            .filter_by(numero_socio=numero_socio, id_periodo=periodo.id_periodo)
            .first()
        )
        if saldo is None:
            saldo = SaldoSocios(numero_socio=numero_socio, id_periodo=periodo.id_periodo)
            session.add(saldo)

        saldo.saldo_anterior = saldo_anterior
        saldo.cargos = cargos
        saldo.pagos = pagos
        saldo.reembolsos = reembolsos
        saldo.devoluciones = devoluciones
        saldo.saldo_actual = saldo_actual
        session.flush()
        logger.info(
            "BalancesService: recalculated numero_socio=%s id_periodo=%s saldo_actual=%s",
            numero_socio, periodo.id_periodo, saldo_actual,
        )
        return saldo

    @staticmethod
    def _sum_tipo(session: Session, numero_socio: str, id_periodo: int, tipo: str) -> Decimal:
        rows = (
            session.query(Transaccion.monto)
            .filter(
                Transaccion.numero_socio == numero_socio,
                Transaccion.id_periodo == id_periodo,
                Transaccion.tipo == tipo,
            )
            .all()
        )
        return sum((row[0] for row in rows), Decimal("0"))
