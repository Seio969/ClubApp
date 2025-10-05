"""Service layer for members menu view.

This module extracts non-UI/backend logic from the UI view so the
presentation layer can remain thin and focused on widgets. It now
includes helpers to discover database tables and fetch "SELECT *"
results dynamically into a Qt model.
"""
from __future__ import annotations

from typing import Any, List, Optional

from services.view_registry import ViewRegistry


class MembersMenuService:
    """Provides backend behaviour for the members menu view.

    Methods in this class are UI-agnostic: they operate on model-like
    objects or return pure data that the UI can consume.
    """

    def search_members(self, text: str, model: Any) -> int:
        """Populate the provided model with results for `text`.

        Returns number of rows added.
        """
        if model is None:
            print("MembersMenuService.search_members: no model provided")
            return 0

        try:
            # Clear existing rows
            model.removeRows(0, model.rowCount())
            if not text:
                return 0

            # Import Qt item lazily to avoid coupling at module import time
            from PySide6.QtGui import QStandardItem

            row = [QStandardItem("1"), QStandardItem(text), QStandardItem("n/a@example.com"), QStandardItem("Activo")]
            model.appendRow(row)
            print(f"MembersMenuService.search_members: added 1 row for '{text}'")
            return 1
        except Exception as exc:
            print("MembersMenuService.search_members: failed -", exc)
            return 0

    def __init__(self) -> None:
        # Delegate view/table discovery and fetching to ViewRegistry
        self._view_registry = ViewRegistry()

    def get_db_tables(self) -> List[str]:
        return self._view_registry.get_db_tables()

    def get_views(self) -> List[str]:
        return self._view_registry.get_views()

    def fetch_view(self, name: str, model: Any, limit: int = 500) -> int:
        """Fetch a registered view (table/sql/callable) and populate the Qt model."""
        if model is None:
            print("MembersMenuService.fetch_view: no model provided")
            return 0
        try:
            keys, rows = self._view_registry.fetch_view(name, limit=limit)
            from PySide6.QtGui import QStandardItem

            model.removeRows(0, model.rowCount())
            model.setColumnCount(len(keys))
            model.setRowCount(0)
            model.setHorizontalHeaderLabels([str(k) for k in keys])
            for row in rows:
                items = [QStandardItem("") if v is None else QStandardItem(str(v)) for v in row]
                model.appendRow(items)
            return len(rows)
        except Exception as exc:
            print("MembersMenuService.fetch_view: failed -", exc)
            return 0

    def fetch_table(self, table_name: str, model: Any, limit: int = 500) -> int:
        """Backward-compatible helper: fetch a table by name and populate model."""
        return self.fetch_view(table_name, model, limit=limit)

    def get_filter_labels(self, model: Optional[Any]) -> List[str]:
        """Return a list of header labels for the provided model.

        The UI will handle visibility state and QAction creation; the
        service only extracts the label strings.
        """
        labels: List[str] = []
        if model is None:
            return labels
        try:
            # Import Qt Orientation lazily so the service is still usable
            # without forcing top-level Qt imports.
            from PySide6.QtCore import Qt

            col_count = model.columnCount()
            for col in range(col_count):
                header = model.headerData(col, Qt.Orientation.Horizontal)
                labels.append(str(header) if header is not None else f"Columna {col}")
        except Exception:
            pass
        return labels
