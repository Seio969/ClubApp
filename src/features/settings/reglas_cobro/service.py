"""Billing rules (ReglaCobro) CRUD service.

Unlike MetodoPago, there's no README-fixed set here - the club can define
as many named rules as it wants (e.g. "Cuota general", "Cuota reducida"),
decided with the user rather than assumed. Every field stays editable.

No rule is ever physically deleted: "remove" always means estado=
"inactivo", the same soft-deactivation pattern used for Socio and
MetodoPago, so a rule's name stays meaningful for anything that already
referenced it once Transacciones/Periodos exist.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.audit import record_log
from database.models import ReglaCobro
from database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)


class ReglasCobroService:
    def list_reglas_cobro(self) -> List[Dict[str, Any]]:
        """Return every billing rule (any estado)."""
        try:
            with get_session() as session:
                rows = session.query(ReglaCobro).order_by(ReglaCobro.id_regla).all()
                return [
                    {
                        "id_regla": row.id_regla,
                        "descripcion": row.descripcion,
                        "cuota_mensual": row.cuota_mensual,
                        "plazo_pago": row.plazo_pago,
                        "penalizacion": row.penalizacion,
                        "descuento": row.descuento,
                        "estado": row.estado,
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.exception("ReglasCobroService.list_reglas_cobro: failed - %s", exc)
            return []

    def get_regla_cobro(self, id_regla: int) -> Optional[Dict[str, Any]]:
        """Fetch a single rule's editable fields, shaped for ReglaCobroDialog."""
        try:
            with get_session() as session:
                regla = session.get(ReglaCobro, id_regla)
                if regla is None:
                    logger.warning("ReglasCobroService.get_regla_cobro: no regla id=%s", id_regla)
                    return None
                return {
                    "descripcion": regla.descripcion,
                    "cuota_mensual": regla.cuota_mensual,
                    "plazo_pago": regla.plazo_pago,
                    "penalizacion": regla.penalizacion,
                    "descuento": regla.descuento,
                }
        except Exception as exc:
            logger.exception("ReglasCobroService.get_regla_cobro: failed id=%s - %s", id_regla, exc)
            return None

    def add_regla_cobro(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new billing rule. Returns its id, or None on failure."""
        try:
            with get_session() as session:
                regla = ReglaCobro(estado="activo", **data)
                session.add(regla)
                session.flush()
                new_id = regla.id_regla
                record_log(
                    session,
                    id_socio=None,
                    accion="crear",
                    tabla_afectada="reglas_cobro",
                    id_registro_afectado=new_id,
                    descripcion_cambio=f"Alta de regla de cobro '{data.get('descripcion')}'",
                )
            logger.info("ReglasCobroService.add_regla_cobro: created id=%s", new_id)
            return new_id
        except Exception as exc:
            logger.exception("ReglasCobroService.add_regla_cobro: failed - %s", exc)
            return None

    def update_regla_cobro(self, id_regla: int, data: Dict[str, Any]) -> bool:
        """Persist edits to an existing billing rule."""
        try:
            with get_session() as session:
                regla = session.get(ReglaCobro, id_regla)
                if regla is None:
                    logger.warning("ReglasCobroService.update_regla_cobro: no regla id=%s", id_regla)
                    return False
                changes = [
                    f"{key}: {getattr(regla, key)!r} -> {value!r}"
                    for key, value in data.items()
                    if getattr(regla, key) != value
                ]
                for key, value in data.items():
                    setattr(regla, key, value)
                record_log(
                    session,
                    id_socio=None,
                    accion="editar",
                    tabla_afectada="reglas_cobro",
                    id_registro_afectado=id_regla,
                    descripcion_cambio="; ".join(changes) if changes else "sin cambios en los campos",
                )
            logger.info("ReglasCobroService.update_regla_cobro: updated id=%s", id_regla)
            return True
        except Exception as exc:
            logger.exception("ReglasCobroService.update_regla_cobro: failed id=%s - %s", id_regla, exc)
            return False

    def set_regla_cobro_estado(self, id_regla: int, estado: str) -> bool:
        """Activate or deactivate a billing rule."""
        try:
            with get_session() as session:
                regla = session.get(ReglaCobro, id_regla)
                if regla is None:
                    logger.warning("ReglasCobroService.set_regla_cobro_estado: no regla id=%s", id_regla)
                    return False
                regla.estado = estado
                record_log(
                    session,
                    id_socio=None,
                    accion="activar" if estado == "activo" else "desactivar",
                    tabla_afectada="reglas_cobro",
                    id_registro_afectado=id_regla,
                    descripcion_cambio=f"Regla de cobro '{regla.descripcion}' marcada como {estado}",
                )
            logger.info("ReglasCobroService.set_regla_cobro_estado: id=%s -> %s", id_regla, estado)
            return True
        except Exception as exc:
            logger.exception("ReglasCobroService.set_regla_cobro_estado: failed id=%s - %s", id_regla, exc)
            return False
