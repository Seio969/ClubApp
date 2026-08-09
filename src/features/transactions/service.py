"""TransactionsService: CRUD/query logic for Transaccion (PLAN.md 2.4).

Backs both entry points decided in PLAN.md 2.4 - the Members toolbar's
"Registrar" shortcut and the standalone Transacciones screen - so both share
this one service (and one TransactionDialog) rather than each growing its
own persistence logic.
"""

from __future__ import annotations

import calendar
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.audit import record_log
from database.models import MetodoPago, Periodo, Socio, Transaccion
from database.session import get_session
from utils.text import normalize_for_match
from utils.logger import get_logger

logger = get_logger(__name__)

TIPOS_TRANSACCION = ("cargo", "pago", "reembolso")

# Columns for the standalone Transacciones screen (list_transactions), in
# display order.
_TRANSACCION_COLUMNS = ("ID", "Fecha", "Socio", "Tipo", "Monto", "Método", "Período", "Referencia")


def _add_months(fecha: datetime.date, months: int) -> datetime.date:
    """Add `months` calendar months to `fecha`, clamping the day if needed."""
    month_index = fecha.month - 1 + months
    year = fecha.year + month_index // 12
    month = month_index % 12 + 1
    day = min(fecha.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


class TransactionsService:
    """Service for transaction operations without direct Qt coupling."""

    def list_socios_activos(self) -> List[Dict[str, Any]]:
        """Return active socios for the transaction dialog's socio picker.

        Ordered by apellidos/nombre so a searchable combo lists them
        alphabetically. Only estado="activo" socios are offered - registering
        a movement for a deactivated member isn't a supported flow yet. Each
        row includes es_titular (PLAN.md 2.17) so the dialog can default its
        visible list to titulares while still resolving a searched-for
        non-titular pick.
        """
        try:
            with get_session() as session:
                rows = (
                    session.query(Socio)
                    .filter(Socio.estado == "activo")
                    .order_by(Socio.apellidos, Socio.nombre)
                    .all()
                )
                return [
                    {
                        "id_socio": s.id_socio,
                        "numero_socio": s.numero_socio,
                        "nombre": s.nombre,
                        "apellidos": s.apellidos,
                        "es_titular": bool(s.es_titular),
                    }
                    for s in rows
                ]
        except Exception as exc:
            logger.exception("TransactionsService.list_socios_activos: failed - %s", exc)
            return []

    def has_titular(self, numero_socio: str) -> bool:
        """Whether numero_socio already has a titular assigned (PLAN.md 2.17).

        Pre-existing numero_socio groups that predate the titular feature
        have none, and are blocked from the transaction dialog's picker
        (both the open search and the Members-toolbar "Registrar" shortcut)
        until an admin assigns one via Members/Ajustes.
        """
        try:
            with get_session() as session:
                return (
                    session.query(Socio)
                    .filter(Socio.numero_socio == numero_socio, Socio.es_titular.is_(True))
                    .first()
                    is not None
                )
        except Exception as exc:
            logger.exception("TransactionsService.has_titular: failed for numero_socio=%s - %s", numero_socio, exc)
            return False

    def list_metodos_pago_activos(self) -> List[Dict[str, Any]]:
        """Return active payment methods for the dialog's método dropdown."""
        try:
            with get_session() as session:
                rows = (
                    session.query(MetodoPago)
                    .filter(MetodoPago.estado == "activo")
                    .order_by(MetodoPago.nombre)
                    .all()
                )
                return [{"id_metodo": m.id_metodo, "nombre": m.nombre} for m in rows]
        except Exception as exc:
            logger.exception("TransactionsService.list_metodos_pago_activos: failed - %s", exc)
            return []

    def list_periodos(self) -> List[Dict[str, Any]]:
        """Return every período, most recently started first."""
        try:
            with get_session() as session:
                rows = session.query(Periodo).order_by(Periodo.fecha_inicio.desc()).all()
                return [
                    {
                        "id_periodo": p.id_periodo,
                        "nombre": p.nombre,
                        "estado": p.estado,
                        "fecha_inicio": p.fecha_inicio,
                        "fecha_fin": p.fecha_fin,
                    }
                    for p in rows
                ]
        except Exception as exc:
            logger.exception("TransactionsService.list_periodos: failed - %s", exc)
            return []

    def list_transactions(
        self,
        text: str = "",
        tipo: Optional[str] = None,
        id_periodo: Optional[int] = None,
        model: Any = None,
        limit: Optional[int] = None,
    ) -> int:
        """Query transacciones (optionally filtered) and populate `model`.

        Filters: `text` matches the socio column (numero_socio or the
        representative name - see below) accent/case-insensitively; `tipo`
        and `id_periodo` are exact matches, either None meaning "any".

        Deliberately does NOT join Transaccion to Socio on numero_socio for
        the display name: numero_socio is a shared, non-unique family
        identifier (see models.py's note), so a join would silently
        duplicate a transaction row once per family member sharing that
        numero_socio. Instead, a numero_socio -> representative display
        name map is built as a separate query and used only for display/
        search text, never joined into the primary result set.
        """
        if model is None:
            logger.warning("TransactionsService.list_transactions: no model provided")
            return 0
        try:
            with get_session() as session:
                query = session.query(Transaccion).order_by(
                    Transaccion.fecha.desc(), Transaccion.id_transaccion.desc()
                )
                if tipo:
                    query = query.filter(Transaccion.tipo == tipo)
                if id_periodo:
                    query = query.filter(Transaccion.id_periodo == id_periodo)
                transacciones = query.all()

                numeros = {t.numero_socio for t in transacciones if t.numero_socio}
                socio_display: Dict[str, str] = {}
                if numeros:
                    # Order titulares first (PLAN.md 2.17) so setdefault below
                    # locks in the titular's name per numero_socio when one
                    # exists, falling back to the first-by-id member of
                    # groups that still have no titular assigned.
                    socios = (
                        session.query(Socio)
                        .filter(Socio.numero_socio.in_(numeros))
                        .order_by(Socio.es_titular.desc(), Socio.id_socio)
                        .all()
                    )
                    for s in socios:
                        socio_display.setdefault(s.numero_socio, f"{s.nombre} {s.apellidos}")

                metodo_names = {m.id_metodo: m.nombre for m in session.query(MetodoPago).all()}
                periodo_names = {p.id_periodo: p.nombre for p in session.query(Periodo).all()}

                rows = []
                for t in transacciones:
                    nombre = socio_display.get(t.numero_socio, "")
                    socio_label = f"{t.numero_socio} · {nombre}" if nombre else str(t.numero_socio)
                    rows.append(
                        (
                            t.id_transaccion,
                            t.fecha,
                            socio_label,
                            t.tipo,
                            t.monto,
                            metodo_names.get(t.id_metodo, ""),
                            periodo_names.get(t.id_periodo, ""),
                            t.referencia or "",
                        )
                    )

            needle = normalize_for_match(text) if text else ""
            if needle:
                rows = [r for r in rows if needle in normalize_for_match(r[2])]
            if limit:
                rows = rows[:limit]

            self._populate_model(model, list(_TRANSACCION_COLUMNS), rows)
            logger.info("TransactionsService.list_transactions: %d rows (tipo=%s, id_periodo=%s)", len(rows), tipo, id_periodo)
            return len(rows)
        except Exception as exc:
            logger.exception("TransactionsService.list_transactions: failed - %s", exc)
            return 0

    @staticmethod
    def _populate_model(model: Any, keys: List[str], rows: List[tuple]) -> None:
        """Rebuild `model` in place from `keys` (headers) and `rows`."""
        from PySide6.QtGui import QStandardItem

        model.removeRows(0, model.rowCount())
        model.setColumnCount(len(keys))
        model.setRowCount(0)
        model.setHorizontalHeaderLabels([str(k) for k in keys])
        for row in rows:
            items = [QStandardItem("") if v is None else QStandardItem(str(v)) for v in row]
            for item in items:
                item.setEditable(False)
            model.appendRow(items)

    def export_transactions(self, rows: Optional[List[List[str]]] = None, destination: Optional[str] = None) -> None:
        """Export plain rows to a destination (placeholder, same shape as
        MembersService.export_members - real export is PLAN.md 2.8's job).
        """
        count = len(rows) if rows is not None else 0
        logger.info("TransactionsService.export_transactions(): placeholder exporting %d rows to %s", count, destination)

    def create_periodo_rapido(self, nombre: str, fecha_inicio: datetime.date) -> Optional[int]:
        """Minimal período creation for the transaction dialog's inline picker.

        Only takes nombre + fecha_inicio (PLAN.md 2.4 decision, made because
        a full períodos management screen - open/close, editing - is still
        2.6's separate, unbuilt job). fecha_fin is derived as one month minus
        a day after fecha_inicio, so Periodo.fecha_fin's NOT NULL constraint
        is satisfied without asking the user for it here.
        """
        nombre = (nombre or "").strip()
        if not nombre or fecha_inicio is None:
            logger.warning("TransactionsService.create_periodo_rapido: nombre/fecha_inicio required")
            return None
        try:
            fecha_fin = _add_months(fecha_inicio, 1) - datetime.timedelta(days=1)
            with get_session() as session:
                periodo = Periodo(
                    nombre=nombre,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    estado="abierto",
                )
                session.add(periodo)
                session.flush()
                new_id = periodo.id_periodo
                record_log(
                    session,
                    id_socio=None,
                    accion="crear",
                    tabla_afectada="periodo",
                    id_registro_afectado=new_id,
                    descripcion_cambio=f"Alta rápida de período '{nombre}' ({fecha_inicio} - {fecha_fin})",
                )
            logger.info("TransactionsService.create_periodo_rapido: created id=%s nombre=%s", new_id, nombre)
            return new_id
        except Exception as exc:
            logger.exception("TransactionsService.create_periodo_rapido: failed - %s", exc)
            return None

    def _sum_by_tipo(self, session: Session, numero_socio: str, id_periodo: int, tipo: str) -> Decimal:
        """Sum monto across every Transaccion of `tipo` for numero_socio+id_periodo."""
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

    def _validate_transaction(self, session: Session, data: Dict[str, Any]) -> Optional[str]:
        """Return an error message if `data` fails an integrity rule, else None.

        Two rules (PLAN.md 2.4, decided):
        - A "reembolso" can't exceed what's actually available to refund:
          sum of "pago" minus sum of already-refunded "reembolso", scoped to
          the same numero_socio+id_periodo (mirrors SaldoSocios' per-período
          scoping).
        - No exact-duplicate Transaccion (same numero_socio/tipo/monto/
          id_periodo/id_metodo/fecha) - catches accidental double-submission
          (e.g. double-clicking "Aceptar") without blocking legitimate
          similar-looking charges that differ in any of those fields.
        """
        numero_socio = data.get("numero_socio")
        id_periodo = data.get("id_periodo")
        tipo = data.get("tipo")
        monto = data.get("monto")

        if tipo == "reembolso":
            pagos = self._sum_by_tipo(session, numero_socio, id_periodo, "pago")
            reembolsos = self._sum_by_tipo(session, numero_socio, id_periodo, "reembolso")
            disponible = pagos - reembolsos
            if monto is None or monto > disponible:
                return (
                    f"No se puede reembolsar {monto}€: el socio {numero_socio} solo tiene "
                    f"{disponible}€ disponibles de pagos en este período."
                )

        duplicate = (
            session.query(Transaccion)
            .filter_by(
                numero_socio=numero_socio,
                tipo=tipo,
                monto=monto,
                id_periodo=id_periodo,
                id_metodo=data.get("id_metodo"),
                fecha=data.get("fecha"),
            )
            .first()
        )
        if duplicate is not None:
            return (
                "Ya existe una transacción idéntica registrada (mismo socio, tipo, "
                "monto, período, método y fecha)."
            )

        return None

    def validate_transaction(self, data: Dict[str, Any]) -> Optional[str]:
        """Public pre-check so the UI can show the specific rejection reason
        before calling add_transaction (which re-validates internally too).

        Returns an error message if `data` fails an integrity rule, else
        None. On an unexpected failure to even run the check, returns a
        generic error rather than None - unlike this codebase's usual
        "log and return an empty/safe default" style, silently returning
        "no error" here would let an unvalidated transaction through.
        """
        try:
            with get_session() as session:
                return self._validate_transaction(session, data)
        except Exception as exc:
            logger.exception("TransactionsService.validate_transaction: failed - %s", exc)
            return "No se pudo validar la transacción; inténtelo de nuevo."

    def add_transaction(self, data: Dict[str, Any]) -> Optional[int]:
        """Persist a new Transaccion. Returns its new id, or None on failure
        (including a failed integrity check - see _validate_transaction).

        `data` keys: numero_socio, id_periodo, id_metodo, tipo, monto, fecha,
        referencia (see TransactionDialog.get_data()), plus an optional
        `id_socio_log` - the individual Socio.id_socio picked in the dialog,
        used only to attribute the audit Log row. Transaccion itself FKs on
        numero_socio (the family), not id_socio - see models.py's note on
        why Log differs from Transaccion here.
        """
        data = dict(data)
        id_socio_log = data.pop("id_socio_log", None)
        try:
            with get_session() as session:
                error = self._validate_transaction(session, data)
                if error:
                    logger.warning("TransactionsService.add_transaction: rejected - %s", error)
                    return None

                transaccion = Transaccion(**data)
                session.add(transaccion)
                session.flush()
                new_id = transaccion.id_transaccion
                record_log(
                    session,
                    id_socio=id_socio_log,
                    accion="crear",
                    tabla_afectada="transacciones",
                    id_registro_afectado=new_id,
                    descripcion_cambio=(
                        f"Alta de {data.get('tipo')} de {data.get('monto')} "
                        f"para numero_socio={data.get('numero_socio')}"
                    ),
                )
            logger.info(
                "TransactionsService.add_transaction: created id=%s tipo=%s numero_socio=%s",
                new_id,
                data.get("tipo"),
                data.get("numero_socio"),
            )
            return new_id
        except Exception as exc:
            logger.exception("TransactionsService.add_transaction: failed - %s", exc)
            return None
