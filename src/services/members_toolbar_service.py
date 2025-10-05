"""Members service containing non-UI behaviour for the members view.

This module implements the logic previously embedded in the UI toolbar.
It is UI-agnostic: methods accept the table/model objects (or simple
callbacks) so the UI layer can pass whatever concrete objects it uses.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional


class MembersService:
    """Provides behaviour for member operations (add, edit, delete, refresh, export).

    The service intentionally does not import Qt UI widgets. It operates on
    the model/table objects given by the caller. This keeps business logic
    decoupled from the presentation layer.
    """

    def add_member(self, parent: Optional[Any] = None) -> None:
        """Open or create a new member entry.

        UI callers may show a dialog by themselves and then call a repository
        or use model manipulation to persist the new member. This method is a
        placeholder for that flow and can be extended to accept callbacks.
        """
        print("MembersService.add_member(): placeholder")

    def edit_member(self, table: Any, model: Any) -> None:
        """Edit the currently selected member.

        Expects the caller to provide the table (selectionModel()) and the
        model (so rows/columns can be inspected). This method performs
        selection checks and returns early if none are selected.
        """
        if table is None:
            print("MembersService.edit_member: no table provided")
            return
        sel = table.selectionModel().selectedRows()
        if not sel:
            print("MembersService.edit_member: no row selected")
            return
        row = sel[0].row()
        if model is not None:
            try:
                id_item = model.item(row, 0)
                print(f"MembersService.edit_member: edit id={id_item.text() if id_item else row}")
            except Exception:
                print(f"MembersService.edit_member: edit row={row}")
        else:
            print(f"MembersService.edit_member: edit row={row}")

    def delete_members(self, table: Any, model: Any) -> int:
        """Delete selected rows from the provided model.

        Returns the number of rows removed.
        """
        if table is None or model is None:
            print("MembersService.delete_members: missing table/model")
            return 0
        sel = table.selectionModel().selectedRows()
        if not sel:
            print("MembersService.delete_members: no row selected")
            return 0
        rows = sorted((s.row() for s in sel), reverse=True)
        for r in rows:
            model.removeRow(r)
        print(f"MembersService.delete_members: removed {len(rows)} rows")
        return len(rows)

    def refresh_members(self, model: Any, sample_count: int = 5) -> int:
        """Refresh the model data. For now, repopulate with sample rows.

        Returns the number of rows added.
        """
        if model is None:
            print("MembersService.refresh_members: no model provided")
            return 0
        try:
            model.removeRows(0, model.rowCount())
            for i in range(1, sample_count + 1):
                # Expecting a Qt model-like API; callers are responsible for
                # passing an appropriate model instance.
                from PySide6.QtGui import QStandardItem

                row = [QStandardItem(str(i)), QStandardItem(f"Miembro {i}"), QStandardItem(f"m{i}@example.com"), QStandardItem("Activo")]
                model.appendRow(row)
            print(f"MembersService.refresh_members: added {sample_count} sample rows")
            return sample_count
        except Exception as exc:
            print("MembersService.refresh_members: failed -", exc)
            return 0

    def export_members(self, model: Any, destination: Optional[str] = None) -> None:
        """Export model contents to a destination (file path or stream).

        This is a placeholder: integrate with utils/exporters.py for full
        export capabilities.
        """
        print(f"MembersService.export_members(): placeholder to {destination}")

    def register_transactions(self, table: Any, model: Any) -> None:
        """Placeholder for registering charges/payments/returns.

        In the future this will open a dialog or wizard to record financial
        movements (cargos, pagos, devoluciones) tied to a member. For now it
        logs context so the UI flow can be exercised.
        """
        if table is None or model is None:
            print("MembersService.register_transactions: no table/model provided")
            return
        sel = table.selectionModel().selectedRows()
        if not sel:
            print("MembersService.register_transactions: no member selected - opening general register")
        else:
            rows = [s.row() for s in sel]
            print(f"MembersService.register_transactions: selected rows={rows}")
