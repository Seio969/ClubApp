"""Payment methods (MetodoPago) CRUD service.

The 5 payment methods fixed by README.md ("Formas de Pago") are always
present (seeded by database.seed_db) and are protected here from renaming
or deactivation-bypass rules that don't apply to custom methods - they can
still be deactivated like any other method, just never renamed or removed
from the fixed set (PLAN.md 2.7, decided).

No method is ever physically deleted: "remove" always means
estado="inactivo", the same soft-deactivation pattern MembersService uses
for Socio (see toolbar_service.py). This keeps a deactivated method's name
meaningful for any transaction that already referenced it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.audit import record_log
from database.models import MetodoPago
from database.seed_db import METODOS_PAGO_FIJOS
from database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)


class MetodosPagoService:
    def is_fixed(self, nombre: str) -> bool:
        return nombre in METODOS_PAGO_FIJOS

    def list_metodos_pago(self) -> List[Dict[str, Any]]:
        """Return every payment method (fixed and custom, any estado)."""
        try:
            with get_session() as session:
                rows = session.query(MetodoPago).order_by(MetodoPago.id_metodo).all()
                return [
                    {
                        "id_metodo": row.id_metodo,
                        "nombre": row.nombre,
                        "estado": row.estado,
                        "fijo": self.is_fixed(row.nombre),
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.exception("MetodosPagoService.list_metodos_pago: failed - %s", exc)
            return []

    def add_metodo_pago(self, nombre: str) -> Optional[int]:
        """Create a new custom payment method. Returns its id, or None on failure."""
        nombre = (nombre or "").strip()
        if not nombre:
            logger.warning("MetodosPagoService.add_metodo_pago: empty nombre")
            return None
        try:
            with get_session() as session:
                metodo = MetodoPago(nombre=nombre, estado="activo")
                session.add(metodo)
                session.flush()
                new_id = metodo.id_metodo
                record_log(
                    session,
                    id_socio=None,
                    accion="crear",
                    tabla_afectada="metodos_pago",
                    id_registro_afectado=new_id,
                    descripcion_cambio=f"Alta de método de pago '{nombre}'",
                )
            logger.info("MetodosPagoService.add_metodo_pago: created id=%s nombre=%s", new_id, nombre)
            return new_id
        except Exception as exc:
            logger.exception("MetodosPagoService.add_metodo_pago: failed to create '%s' - %s", nombre, exc)
            return None

    def rename_metodo_pago(self, id_metodo: int, nuevo_nombre: str) -> bool:
        """Rename a custom payment method. Fixed methods can't be renamed."""
        nuevo_nombre = (nuevo_nombre or "").strip()
        if not nuevo_nombre:
            logger.warning("MetodosPagoService.rename_metodo_pago: empty nuevo_nombre")
            return False
        try:
            with get_session() as session:
                metodo = session.get(MetodoPago, id_metodo)
                if metodo is None:
                    logger.warning("MetodosPagoService.rename_metodo_pago: no metodo id=%s", id_metodo)
                    return False
                if self.is_fixed(metodo.nombre):
                    logger.warning(
                        "MetodosPagoService.rename_metodo_pago: '%s' is fixed, refusing rename", metodo.nombre
                    )
                    return False
                old_nombre = metodo.nombre
                metodo.nombre = nuevo_nombre
                record_log(
                    session,
                    id_socio=None,
                    accion="editar",
                    tabla_afectada="metodos_pago",
                    id_registro_afectado=id_metodo,
                    descripcion_cambio=f"nombre: '{old_nombre}' -> '{nuevo_nombre}'",
                )
            logger.info("MetodosPagoService.rename_metodo_pago: id=%s renamed to '%s'", id_metodo, nuevo_nombre)
            return True
        except Exception as exc:
            logger.exception("MetodosPagoService.rename_metodo_pago: failed id=%s - %s", id_metodo, exc)
            return False

    def set_metodo_pago_estado(self, id_metodo: int, estado: str) -> bool:
        """Activate or deactivate a payment method (fixed or custom)."""
        try:
            with get_session() as session:
                metodo = session.get(MetodoPago, id_metodo)
                if metodo is None:
                    logger.warning("MetodosPagoService.set_metodo_pago_estado: no metodo id=%s", id_metodo)
                    return False
                metodo.estado = estado
                record_log(
                    session,
                    id_socio=None,
                    accion="activar" if estado == "activo" else "desactivar",
                    tabla_afectada="metodos_pago",
                    id_registro_afectado=id_metodo,
                    descripcion_cambio=f"Método de pago '{metodo.nombre}' marcado como {estado}",
                )
            logger.info("MetodosPagoService.set_metodo_pago_estado: id=%s -> %s", id_metodo, estado)
            return True
        except Exception as exc:
            logger.exception("MetodosPagoService.set_metodo_pago_estado: failed id=%s - %s", id_metodo, exc)
            return False
