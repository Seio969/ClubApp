"""Audit-log helper.

Centralizes how Log rows get created so every write service inserts them
the same way, inside the same DB transaction as the write itself, rather
than each service hand-rolling its own Log(...) construction - PLAN.md
2.12. Call this from inside an open `get_session()` block, before it
commits: a rollback then undoes the write and its log entry together.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from database.models import Log


def record_log(
    session: Session,
    *,
    id_socio: Optional[int],
    accion: str,
    tabla_afectada: str,
    id_registro_afectado: Optional[int],
    descripcion_cambio: str,
) -> None:
    """Add a Log row to `session` (not committed here).

    id_socio is the individual (Socio.id_socio) the change is attributed
    to - matches Log's FK, which is deliberately on id_socio rather than
    the shared numero_socio family identifier (see models.py).
    """
    session.add(
        Log(
            id_socio=id_socio,
            accion=accion,
            tabla_afectada=tabla_afectada,
            id_registro_afectado=id_registro_afectado,
            descripcion_cambio=descripcion_cambio,
        )
    )
