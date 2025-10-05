"""Service layer for members menu view.

This module extracts non-UI/backend logic from the UI view so the
presentation layer can remain thin and focused on widgets.
"""
from __future__ import annotations

from typing import Any, List, Optional


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

    def get_demo_views(self, count: int = 12) -> List[str]:
        """Return a list of demo view names for the UI to display."""
        return [f"Vista {i+1}" for i in range(count)]

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
