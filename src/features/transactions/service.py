"""TransactionsService: CRUD/query logic for Transaccion (PLAN.md 2.4).

Backs both entry points decided in PLAN.md 2.4 - the Members toolbar's
"Registrar" shortcut and the standalone Transacciones screen - so both share
this one service (and one TransactionDialog) rather than each growing its
own persistence logic.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from database.audit import record_log
from database.models import MetodoPago, Periodo, Socio, Transaccion
from database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)

TIPOS_TRANSACCION = ("cargo", "pago", "reembolso")


def _add_months(fecha: datetime.date, months: int) -> datetime.date:
    """Add `months` calendar months to `fecha`, clamping the day if needed."""
    month_index = fecha.month - 1 + months
    year = fecha.year + month_index // 12
    month = month_index % 12 + 1
    day = min(fecha.day, _days_in_month(year, month))
    return datetime.date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    return (next_month - datetime.timedelta(days=1)).day


class TransactionsService:
    """Service for transaction operations without direct Qt coupling."""

    def list_socios_activos(self) -> List[Dict[str, Any]]:
        """Return active socios for the transaction dialog's socio picker.

        Ordered by apellidos/nombre so a searchable combo lists them
        alphabetically. Only estado="activo" socios are offered - registering
        a movement for a deactivated member isn't a supported flow yet.
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
                    }
                    for s in rows
                ]
        except Exception as exc:
            logger.exception("TransactionsService.list_socios_activos: failed - %s", exc)
            return []

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

    def add_transaction(self, data: Dict[str, Any]) -> Optional[int]:
        """Persist a new Transaccion. Returns its new id, or None on failure.

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
