"""AuditLogService: read-only query logic for Log rows (PLAN.md 2.12).

Every write service already records Log rows via database/audit.py's
record_log() - this service only reads them back for the viewer screen
(Ajustes > Registro de auditoría). No CRUD here: Log rows are a permanent
audit trail, same append-only rule as Transaccion.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.models import Log, Socio
from database.session import get_session
from utils.text import normalize_for_match
from utils.logger import get_logger

logger = get_logger(__name__)

_LOG_COLUMNS = ("ID", "Fecha y hora", "Socio", "Acción", "Tabla", "Registro", "Descripción")
# Columns (by index into the row tuples built in list_logs) matched against
# the search text: Socio, Acción, Descripción - not Tabla/Registro, which
# have their own dedicated filter/id semantics.
_SEARCH_COLS = (2, 3, 6)


class AuditLogService:
    """Provides read-only access to Log rows for the audit viewer screen."""

    def list_tablas_afectadas(self) -> List[str]:
        """Distinct, non-empty tabla_afectada values present in logs, for
        the viewer's filter dropdown."""
        try:
            with get_session() as session:
                rows = session.query(Log.tabla_afectada).distinct().all()
                return sorted({r[0] for r in rows if r[0]})
        except Exception as exc:
            logger.exception("AuditLogService.list_tablas_afectadas: failed - %s", exc)
            return []

    def list_logs(self, text: str = "", tabla_afectada: Optional[str] = None, model: Any = None) -> int:
        """Query logs (optionally filtered) and populate `model`.

        Filters: `text` matches socio/acción/descripción accent/case-
        insensitively; `tabla_afectada` is an exact match, None meaning
        "any". Ordered most-recent-first, matching a timeline/audit-trail
        reading order.
        """
        if model is None:
            logger.warning("AuditLogService.list_logs: no model provided")
            return 0
        try:
            with get_session() as session:
                query = session.query(Log).order_by(Log.fecha_hora.desc(), Log.id_log.desc())
                if tabla_afectada:
                    query = query.filter(Log.tabla_afectada == tabla_afectada)
                logs = query.all()

                socio_ids = {l.id_socio for l in logs if l.id_socio}
                socio_names: Dict[int, str] = {}
                if socio_ids:
                    socios = session.query(Socio).filter(Socio.id_socio.in_(socio_ids)).all()
                    socio_names = {s.id_socio: f"{s.nombre} {s.apellidos}" for s in socios}

                rows = []
                for l in logs:
                    socio_label = socio_names.get(l.id_socio, "") if l.id_socio else ""
                    rows.append(
                        (
                            l.id_log,
                            l.fecha_hora,
                            socio_label,
                            l.accion,
                            l.tabla_afectada or "",
                            l.id_registro_afectado if l.id_registro_afectado is not None else "",
                            l.descripcion_cambio or "",
                        )
                    )

            needle = normalize_for_match(text) if text else ""
            if needle:
                rows = [
                    r for r in rows
                    if any(needle in normalize_for_match(r[i]) for i in _SEARCH_COLS)
                ]

            self._populate_model(model, list(_LOG_COLUMNS), rows)
            logger.info("AuditLogService.list_logs: %d rows (tabla_afectada=%s)", len(rows), tabla_afectada)
            return len(rows)
        except Exception as exc:
            logger.exception("AuditLogService.list_logs: failed - %s", exc)
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
