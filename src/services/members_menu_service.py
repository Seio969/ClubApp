"""Service layer for members menu view.

This module extracts non-UI/backend logic from the UI view so the
presentation layer can remain thin and focused on widgets. It now
includes helpers to discover database tables and fetch "SELECT *"
results dynamically into a Qt model.
"""
from __future__ import annotations

from typing import Any, List, Optional

from database.session import engine
from sqlalchemy import text
from sqlalchemy import inspect as sqlalchemy_inspect


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

    # ------------------------------------------------------------------
    def get_db_tables(self) -> List[str]:
        """Return a list of table names present in the configured database.

        This uses SQLAlchemy's inspector so it is safe and database-agnostic.
        """
        try:
            inspector = sqlalchemy_inspect(engine)
            tables = inspector.get_table_names()
            return tables
        except Exception as exc:
            print("MembersMenuService.get_db_tables: failed -", exc)
            return []

    def fetch_table(self, table_name: str, model: Any, limit: int = 500) -> int:
        """Execute a SELECT * FROM <table_name> and populate the provided Qt model.

        The table_name is validated against the database's table list to
        avoid SQL injection. Returns number of rows added.
        """
        if model is None:
            print("MembersMenuService.fetch_table: no model provided")
            return 0

        try:
            tables = self.get_db_tables()
            if table_name not in tables:
                print(f"MembersMenuService.fetch_table: unknown table '{table_name}'")
                return 0

            # Run the query. table_name is safe because we validated it above.
            stmt = text(f'SELECT * FROM "{table_name}" LIMIT :limit')
            with engine.connect() as conn:
                res = conn.execute(stmt, {"limit": limit})
                rows = res.fetchall()
                keys = res.keys()

            # Populate the Qt model
            from PySide6.QtGui import QStandardItem

            # Clear and set columns
            model.removeRows(0, model.rowCount())
            model.setColumnCount(len(keys))
            model.setRowCount(0)
            model.setHorizontalHeaderLabels([str(k) for k in keys])

            for row in rows:
                items = [QStandardItem("") if v is None else QStandardItem(str(v)) for v in row]
                model.appendRow(items)

            return len(rows)
        except Exception as exc:
            print("MembersMenuService.fetch_table: failed -", exc)
            return 0

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
