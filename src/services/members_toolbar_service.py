"""Members service implementing UI-free backend behaviour for members.

This service accepts simple data (row indices, plain row data) and
returns primitive results so the UI layer can remain responsible for
Qt-specific objects and conversions.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Any


class MembersService:
    """Service for member operations without direct Qt coupling.

    Methods operate on plain data structures (lists, callbacks) so they're
    easy to unit test and independent from PySide6.
    """

    def add_member(self, parent: Optional[Any] = None) -> None:
        """Placeholder for creating a new member."""
        print("MembersService.add_member(): placeholder")

    def edit_member(self, selected_indices: List[int], model_getter: Optional[Callable[[int, int], Any]] = None) -> None:
        """Prepare an edit operation for the first selected index.

        - selected_indices: list of selected row indices (may be empty)
        - model_getter: optional callable (row, col) -> item-like object
        """
        if not selected_indices:
            print("MembersService.edit_member: no row selected")
            return
        row = selected_indices[0]
        if model_getter is not None:
            try:
                id_item = model_getter(row, 0)
                # If the getter returns a Qt item-like object, attempt to
                # read a text/value attribute in a best-effort manner.
                val = getattr(id_item, "text", lambda: id_item)()
                print(f"MembersService.edit_member: edit id={val}")
            except Exception:
                print(f"MembersService.edit_member: edit row={row}")
        else:
            print(f"MembersService.edit_member: edit row={row}")

    def delete_members(self, selected_indices: List[int]) -> List[int]:
        """Return a list of row indices to delete, sorted in reverse order.

        The UI should perform the actual deletion on its model to avoid
        coupling the service to Qt APIs.
        """
        if not selected_indices:
            print("MembersService.delete_members: no row selected")
            return []
        rows = sorted(set(selected_indices), reverse=True)
        print(f"MembersService.delete_members: will remove {len(rows)} rows: {rows}")
        return rows

    def refresh_members(self, sample_count: int = 5) -> List[List[str]]:
        """Return plain row data to populate the UI model.

        Each row is a list of string values: [id, name, email, status].
        """
        data: List[List[str]] = []
        for i in range(1, sample_count + 1):
            data.append([str(i), f"Miembro {i}", f"m{i}@example.com", "Activo"])
        print(f"MembersService.refresh_members: prepared {len(data)} sample rows")
        return data

    def export_members(self, rows: Optional[List[List[str]]] = None, destination: Optional[str] = None) -> None:
        """Export plain rows to a destination (placeholder).

        The UI should extract model data into `rows` before calling this.
        """
        count = len(rows) if rows is not None else 0
        print(f"MembersService.export_members(): placeholder exporting {count} rows to {destination}")

    def register_transactions(self, selected_indices: List[int]) -> None:
        """Handle transaction registration for given selected indices."""
        if not selected_indices:
            print("MembersService.register_transactions: no member selected - opening general register")
            return
        print(f"MembersService.register_transactions: selected rows={selected_indices}")
