"""View registry and DB-backed view helpers.

This module centralizes logic for discovering tables and registering
named "views" (table-backed, SQL-backed or callable) and fetching their
results into Qt models. It was extracted from MembersMenuService to keep
concerns separated and make view registration reusable.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Tuple

from database.session import engine
from sqlalchemy import text
from sqlalchemy import inspect as sqlalchemy_inspect


class ViewRegistry:
    """Registry of named views and helpers to fetch them.

    The registry stores entries of type table/sql/callable and exposes
    methods to register, list and fetch views into a Qt model.
    """

    def __init__(self) -> None:
        self._views: dict[str, dict] = {}
        try:
            for t in self.get_db_tables():
                self.register_table_view(t, description="Tabla: " + t)
        except Exception:
            # inspector might fail in some test environments; ignore
            pass

    def get_db_tables(self) -> List[str]:
        """Return list of table names from the configured database."""
        try:
            inspector = sqlalchemy_inspect(engine)
            return inspector.get_table_names()
        except Exception as exc:
            print("ViewRegistry.get_db_tables: failed -", exc)
            return []

    def register_table_view(self, name: str, description: Optional[str] = None) -> None:
        self._views[name] = {"type": "table", "value": name, "desc": description or ""}

    def register_sql_view(self, name: str, sql: str, description: Optional[str] = None) -> None:
        self._views[name] = {"type": "sql", "value": sql, "desc": description or ""}

    def register_callable_view(self, name: str, func, description: Optional[str] = None) -> None:
        self._views[name] = {"type": "callable", "value": func, "desc": description or ""}

    def get_views(self) -> List[str]:
        return list(self._views.keys())

    def fetch_table(self, table_name: str, limit: int = 500) -> Tuple[List[str], List[tuple]]:
        """Return (keys, rows) for SELECT * FROM table_name.

        This returns data rather than mutating a Qt model so the caller
        can decide how to populate the UI.
        """
        try:
            if table_name not in self.get_db_tables():
                raise ValueError(f"Unknown table: {table_name}")
            stmt = text(f'SELECT * FROM "{table_name}" LIMIT :limit')
            with engine.connect() as conn:
                res = conn.execute(stmt, {"limit": limit})
                rows = res.fetchall()
                keys = list(res.keys())
            return keys, rows
        except Exception as exc:
            print("ViewRegistry.fetch_table: failed -", exc)
            return [], []

    def fetch_view(self, name: str, limit: int = 500) -> Tuple[List[str], List[tuple]]:
        """Fetch a registered view and return (keys, rows).

        Supports table, sql and callable view types.
        """
        if name not in self._views:
            # fallback: if name matches a db table, fetch it
            if name in self.get_db_tables():
                return self.fetch_table(name, limit=limit)
            print(f"ViewRegistry.fetch_view: unknown view '{name}'")
            return [], []

        entry = self._views[name]
        vtype = entry.get("type")

        try:
            if vtype == "table":
                return self.fetch_table(entry["value"], limit=limit)

            if vtype == "sql":
                sql = entry["value"]
                try:
                    stmt = text(f"{sql} LIMIT :limit")
                    with engine.connect() as conn:
                        res = conn.execute(stmt, {"limit": limit})
                        rows = res.fetchall()
                        keys = list(res.keys())
                except Exception:
                    with engine.connect() as conn:
                        res = conn.execute(text(sql))
                        rows = res.fetchall()
                        keys = list(res.keys())
                return keys, rows

            if vtype == "callable":
                func = entry["value"]
                keys, rows = func()
                return list(keys), list(rows)

        except Exception as exc:
            print("ViewRegistry.fetch_view: failed -", exc)
            return [], []
