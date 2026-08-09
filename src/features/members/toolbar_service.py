"""Members service implementing UI-free backend behaviour for members.

This service accepts simple data (row indices, plain row data) and
returns primitive results so the UI layer can remain responsible for
Qt-specific objects and conversions.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

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

    def get_titular(self, numero_socio: str) -> Optional[Dict[str, Any]]:
        """Return the current titular (primary holder) for numero_socio.

        Returns a plain dict with id_socio/numero_socio/nombre/apellidos, or
        None if numero_socio has no titular set (either it doesn't exist yet
        or it's one of the pre-existing groups left unset - see PLAN.md 2.17).
        """
        try:
            with get_session() as session:
                socio = (
                    session.query(Socio)
                    .filter(Socio.numero_socio == numero_socio, Socio.es_titular.is_(True))
                    .first()
                )
                if socio is None:
                    return None
                return {
                    "id_socio": socio.id_socio,
                    "numero_socio": socio.numero_socio,
                    "nombre": socio.nombre,
                    "apellidos": socio.apellidos,
                }
        except Exception as exc:
            logger.exception("MembersService.get_titular: failed for numero_socio=%s - %s", numero_socio, exc)
            return None

    @staticmethod
    def _unset_other_titulares(session, numero_socio: str, exclude_id_socio: int) -> Optional[Socio]:
        """Unset es_titular on any other Socio sharing numero_socio.

        Returns the Socio row that was the titular before being unset (for
        audit-log attribution), or None if there wasn't one. Doesn't commit -
        caller runs this inside its own get_session() block.
        """
        others = (
            session.query(Socio)
            .filter(
                Socio.numero_socio == numero_socio,
                Socio.es_titular.is_(True),
                Socio.id_socio != exclude_id_socio,
            )
            .all()
        )
        previous = others[0] if others else None
        for other in others:
            other.es_titular = False
        return previous

    def add_member(self, data: Dict[str, Any]) -> Optional[int]:
        """Persist a new member (Socio) to the database.

        `data` should contain the Socio field values (see MemberDialog.get_data).
        Returns the new row's id_socio on success, or None on failure.

        Titular handling (PLAN.md 2.17): a brand-new numero_socio always gets
        its first Socio row marked es_titular=True, overriding whatever the
        form sent - there's no valid "unset" state for a new número. For an
        existing numero_socio, if the new row is created as titular, any
        other titular sharing that número is auto-unset (with its own
        "cambio_titular" log row) - never two titulares at once.
        """
        data = dict(data)
        try:
            with get_session() as session:
                numero_socio = data.get("numero_socio")
                is_new_numero = (
                    session.query(Socio).filter(Socio.numero_socio == numero_socio).first() is None
                )
                if is_new_numero:
                    data["es_titular"] = True

                socio = Socio(**data)
                session.add(socio)
                session.flush()  # populate id_socio before the session closes
                new_id = socio.id_socio

                if socio.es_titular:
                    previous = self._unset_other_titulares(session, numero_socio, exclude_id_socio=new_id)
                    if previous is not None:
                        record_log(
                            session,
                            id_socio=new_id,
                            accion="cambio_titular",
                            tabla_afectada="socios",
                            id_registro_afectado=new_id,
                            descripcion_cambio=(
                                f"Titular de numero_socio={numero_socio} cambiado de "
                                f"{previous.nombre} {previous.apellidos} (id_socio={previous.id_socio}) "
                                f"a {socio.nombre} {socio.apellidos} (id_socio={new_id})"
                            ),
                        )

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
                    "es_titular": bool(socio.es_titular),
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
                numero_socio = data.get("numero_socio", socio.numero_socio)
                becoming_titular = bool(data.get("es_titular")) and not socio.es_titular
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
                if becoming_titular:
                    previous = self._unset_other_titulares(session, numero_socio, exclude_id_socio=id_socio)
                    if previous is not None:
                        record_log(
                            session,
                            id_socio=id_socio,
                            accion="cambio_titular",
                            tabla_afectada="socios",
                            id_registro_afectado=id_socio,
                            descripcion_cambio=(
                                f"Titular de numero_socio={numero_socio} cambiado de "
                                f"{previous.nombre} {previous.apellidos} (id_socio={previous.id_socio}) "
                                f"a {socio.nombre} {socio.apellidos} (id_socio={id_socio})"
                            ),
                        )
            logger.info("MembersService.update_member: updated socio id_socio=%s", id_socio)
            return True
        except Exception as exc:
            logger.exception("MembersService.update_member: failed to update id_socio=%s - %s", id_socio, exc)
            return False

    def set_socio_estado(self, id_socio: int, estado: str) -> bool:
        """Activate or deactivate a member.

        Sets estado via UPDATE - never a physical DELETE, so transaction/
        balance/log history referencing the member is preserved. Same
        activar/desactivar shape as MetodosPagoService.set_metodo_pago_estado
        and ReglasCobroService.set_regla_cobro_estado, except the audit Log
        row is attributed to the member itself (id_socio=id_socio) rather
        than id_socio=None, since Log FKs on id_socio for the individual.
        """
        try:
            with get_session() as session:
                socio = session.get(Socio, id_socio)
                if socio is None:
                    logger.warning("MembersService.set_socio_estado: no socio with id_socio=%s", id_socio)
                    return False
                socio.estado = estado
                record_log(
                    session,
                    id_socio=id_socio,
                    accion="activar" if estado == "activo" else "desactivar",
                    tabla_afectada="socios",
                    id_registro_afectado=id_socio,
                    descripcion_cambio=f"Socio numero_socio={socio.numero_socio} marcado como {estado}",
                )
            logger.info("MembersService.set_socio_estado: id_socio=%s -> %s", id_socio, estado)
            return True
        except Exception as exc:
            logger.exception("MembersService.set_socio_estado: failed id_socio=%s - %s", id_socio, exc)
            return False


    def export_members(self, rows: Optional[List[List[str]]] = None, destination: Optional[str] = None) -> None:
        """Export plain rows to a destination (placeholder).

        The UI should extract model data into `rows` before calling this.
        """
        count = len(rows) if rows is not None else 0
        logger.info("MembersService.export_members(): placeholder exporting %d rows to %s", count, destination)
