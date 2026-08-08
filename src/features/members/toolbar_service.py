"""Members service implementing UI-free backend behaviour for members.

This service accepts simple data (row indices, plain row data) and
returns primitive results so the UI layer can remain responsible for
Qt-specific objects and conversions.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Any

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
            logger.info(
                "MembersService.add_member: created socio id=%s numero_socio=%s",
                new_id,
                data.get("numero_socio"),
            )
            return new_id
        except Exception as exc:
            logger.exception("MembersService.add_member: failed to create member - %s", exc)
            return None

    def edit_member(self, selected_indices: List[int], model_getter: Optional[Callable[[int, int], Any]] = None) -> None:
        """Prepare an edit operation for the first selected index.

        - selected_indices: list of selected row indices (may be empty)
        - model_getter: optional callable (row, col) -> item-like object
        """
        if not selected_indices:
            logger.warning("MembersService.edit_member: no row selected")
            return
        row = selected_indices[0]
        if model_getter is not None:
            try:
                id_item = model_getter(row, 0)
                # If the getter returns a Qt item-like object, attempt to
                # read a text/value attribute in a best-effort manner.
                val = getattr(id_item, "text", lambda: id_item)()
                logger.info("MembersService.edit_member: edit id=%s", val)
            except Exception:
                logger.info("MembersService.edit_member: edit row=%s", row)
        else:
            logger.info("MembersService.edit_member: edit row=%s", row)

    def delete_members(self, selected_indices: List[int]) -> List[int]:
        """Return a list of row indices to delete, sorted in reverse order.

        The UI should perform the actual deletion on its model to avoid
        coupling the service to Qt APIs.
        """
        if not selected_indices:
            logger.warning("MembersService.delete_members: no row selected")
            return []
        rows = sorted(set(selected_indices), reverse=True)
        logger.info("MembersService.delete_members: will remove %d rows: %s", len(rows), rows)
        return rows


    def export_members(self, rows: Optional[List[List[str]]] = None, destination: Optional[str] = None) -> None:
        """Export plain rows to a destination (placeholder).

        The UI should extract model data into `rows` before calling this.
        """
        count = len(rows) if rows is not None else 0
        logger.info("MembersService.export_members(): placeholder exporting %d rows to %s", count, destination)

    def register_transactions(self, selected_indices: List[int]) -> None:
        """Handle transaction registration for given selected indices."""
        if not selected_indices:
            logger.info("MembersService.register_transactions: no member selected - opening general register")
            return
        logger.info("MembersService.register_transactions: selected rows=%s", selected_indices)
