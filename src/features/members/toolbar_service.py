"""Members service implementing UI-free backend behaviour for members.

This service accepts simple data (row indices, plain row data) and
returns primitive results so the UI layer can remain responsible for
Qt-specific objects and conversions.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Any

from database.audit import record_log
from database.models import Socio
from database.session import get_session
from utils.logger import get_logger
logger = get_logger(__name__)


class MembersService:
    """Service for member operations without direct Qt coupling.

    Methods operate on plain data structures (lists, callbacks) so they're
    easy to unit test and independent from PySide6.
    """

    def add_member(self, data: Dict[str, Any]) -> Optional[int]:
        """Persist a new member (Socio) to the database.

        `data` should contain the Socio field values (see MemberDialog.get_data).
        Returns the new row's id_socio on success, or None on failure.
        """
        try:
            with get_session() as session:
                socio = Socio(**data)
                session.add(socio)
                session.flush()  # populate id_socio before the session closes
                new_id = socio.id_socio
                record_log(
                    session,
                    id_socio=new_id,
                    accion="crear",
                    tabla_afectada="socios",
                    id_registro_afectado=new_id,
                    descripcion_cambio=(
                        f"Alta de socio numero_socio={data.get('numero_socio')} "
                        f"nombre={data.get('nombre')} {data.get('apellidos')}"
                    ),
                )
            logger.info(
                "MembersService.add_member: created socio id=%s numero_socio=%s",
                new_id,
                data.get("numero_socio"),
            )
            return new_id
        except Exception as exc:
            logger.exception("MembersService.add_member: failed to create member - %s", exc)
            return None

    def get_member(self, id_socio: int) -> Optional[Dict[str, Any]]:
        """Fetch a single member's editable fields by id_socio.

        Returns a dict shaped like MemberDialog.get_data()'s output (ready
        to pre-populate the edit dialog), or None if no such member exists
        or the fetch fails.
        """
        try:
            with get_session() as session:
                socio = session.get(Socio, id_socio)
                if socio is None:
                    logger.warning("MembersService.get_member: no socio with id_socio=%s", id_socio)
                    return None
                return {
                    "numero_socio": socio.numero_socio,
                    "nombre": socio.nombre,
                    "apellidos": socio.apellidos,
                    "telefono": socio.telefono,
                    "email": socio.email,
                    "fecha_alta": socio.fecha_alta,
                    "estado": socio.estado,
                    "observaciones": socio.observaciones,
                }
        except Exception as exc:
            logger.exception("MembersService.get_member: failed to fetch id_socio=%s - %s", id_socio, exc)
            return None

    def update_member(self, id_socio: int, data: Dict[str, Any]) -> bool:
        """Persist edits to an existing member (Socio).

        `data` should contain the Socio field values (see
        MemberDialog.get_data()). Returns True on success, False if the
        member doesn't exist or the update fails.
        """
        try:
            with get_session() as session:
                socio = session.get(Socio, id_socio)
                if socio is None:
                    logger.warning("MembersService.update_member: no socio with id_socio=%s", id_socio)
                    return False
                changes = [
                    f"{key}: {getattr(socio, key)!r} -> {value!r}"
                    for key, value in data.items()
                    if getattr(socio, key) != value
                ]
                for key, value in data.items():
                    setattr(socio, key, value)
                record_log(
                    session,
                    id_socio=id_socio,
                    accion="editar",
                    tabla_afectada="socios",
                    id_registro_afectado=id_socio,
                    descripcion_cambio="; ".join(changes) if changes else "sin cambios en los campos",
                )
            logger.info("MembersService.update_member: updated socio id_socio=%s", id_socio)
            return True
        except Exception as exc:
            logger.exception("MembersService.update_member: failed to update id_socio=%s - %s", id_socio, exc)
            return False

    def delete_members(self, selected_indices: List[int], model_getter: Optional[Callable[[int, int], Any]] = None) -> List[int]:
        """Deactivate (soft-delete) the members at the given row indices.

        Sets estado="inactivo" via UPDATE for each resolved id_socio - never
        a physical DELETE, so transaction/balance/log history referencing
        the member is preserved.

        - selected_indices: list of selected row indices (may be empty)
        - model_getter: callable (row, col) -> item-like object, used to
          read column 0 (id_socio) for each selected row.

        Returns the row indices (deduped, sorted descending) that were
        successfully deactivated, so the caller can safely remove those
        rows from its Qt model without index shifting.
        """
        if not selected_indices:
            logger.warning("MembersService.delete_members: no row selected")
            return []
        rows = sorted(set(selected_indices), reverse=True)
        if model_getter is None:
            logger.warning("MembersService.delete_members: no model_getter provided, cannot resolve id_socio")
            return []

        deactivated_rows: List[int] = []
        for row in rows:
            try:
                id_item = model_getter(row, 0)
                val = getattr(id_item, "text", lambda: id_item)()
                id_socio = int(val)
            except Exception:
                logger.exception("MembersService.delete_members: could not resolve id_socio for row=%s", row)
                continue

            try:
                with get_session() as session:
                    socio = session.get(Socio, id_socio)
                    if socio is None:
                        logger.warning("MembersService.delete_members: no socio with id_socio=%s", id_socio)
                        continue
                    socio.estado = "inactivo"
                    record_log(
                        session,
                        id_socio=id_socio,
                        accion="desactivar",
                        tabla_afectada="socios",
                        id_registro_afectado=id_socio,
                        descripcion_cambio=f"Socio numero_socio={socio.numero_socio} marcado como inactivo",
                    )
                logger.info("MembersService.delete_members: deactivated socio id_socio=%s", id_socio)
                deactivated_rows.append(row)
            except Exception as exc:
                logger.exception("MembersService.delete_members: failed to deactivate id_socio=%s - %s", id_socio, exc)

        return deactivated_rows


    def export_members(self, rows: Optional[List[List[str]]] = None, destination: Optional[str] = None) -> None:
        """Export plain rows to a destination (placeholder).

        The UI should extract model data into `rows` before calling this.
        """
        count = len(rows) if rows is not None else 0
        logger.info("MembersService.export_members(): placeholder exporting %d rows to %s", count, destination)
