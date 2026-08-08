"""Service layer for members menu view.

This module extracts non-UI/backend logic from the UI view so the
presentation layer can remain thin and focused on widgets. Members'
data comes from a real, members-owned query over socios - the generic
"browse any DB table" path this used to delegate to (ViewRegistry) was
retired from this screen entirely (PLAN.md 2.16); ViewRegistry itself
stays available as cross-cutting plumbing in common/view_registry.py
for whatever future screen needs it next.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from database.models import Socio
from database.session import get_session
from utils.text import normalize_for_match
from utils.logger import get_logger
logger = get_logger(__name__)

# Columns returned by the real socios query, in display order. Mirrors what
# `SELECT * FROM socios` (the old ViewRegistry-backed default load) showed,
# so switching the default load onto this path doesn't change the columns
# the Members table/Filtros menu present.
_SOCIO_COLUMNS: Tuple[str, ...] = (
    "id_socio",
    "numero_socio",
    "nombre",
    "apellidos",
    "telefono",
    "email",
    "fecha_alta",
    "estado",
    "observaciones",
)
# Columns matched against the search text.
_SOCIO_SEARCH_COLUMNS: Tuple[str, ...] = ("numero_socio", "nombre", "apellidos", "email")


class MembersMenuService:
    """Provides backend behaviour for the members menu view.

    Methods in this class are UI-agnostic: they operate on model-like
    objects or return pure data that the UI can consume.
    """

    def _fetch_socios_rows(self) -> List[tuple]:
        """Return every Socio row as plain tuples, in `_SOCIO_COLUMNS` order.

        Deliberately does not filter by estado - deactivated members still
        need to be searchable/visible here until estado-aware
        filtering/display is built (PLAN.md 2.2).
        """
        with get_session() as session:
            socios = session.query(Socio).order_by(Socio.id_socio).all()
            return [tuple(getattr(s, col) for col in _SOCIO_COLUMNS) for s in socios]

    def _filter_socio_rows(self, rows: List[tuple], text: Optional[str]) -> List[tuple]:
        """Filter `rows` (as returned by `_fetch_socios_rows`) by `text`.

        Matches substrings of numero_socio/nombre/apellidos/email,
        accent- and case-insensitively (via normalize_for_match, shared
        with TableSortMixin's sort-key normalization). Empty/whitespace-only
        text means "no filter" - all rows are returned.
        """
        needle = normalize_for_match(text) if text else ""
        if not needle:
            return rows
        search_idx = [_SOCIO_COLUMNS.index(c) for c in _SOCIO_SEARCH_COLUMNS]
        matched = []
        for row in rows:
            haystack = " ".join(normalize_for_match(row[i]) for i in search_idx if row[i] is not None)
            if needle in haystack:
                matched.append(row)
        return matched

    @staticmethod
    def _populate_model(model: Any, keys: List[str], rows: List[tuple]) -> None:
        """Rebuild `model` in place from `keys` (headers) and `rows`."""
        from PySide6.QtGui import QStandardItem

        model.removeRows(0, model.rowCount())
        model.setColumnCount(len(keys))
        model.setRowCount(0)
        model.setHorizontalHeaderLabels([str(k) for k in keys])
        for row in rows:
            items = [QStandardItem("") if v is None else QStandardItem(str(v)) for v in row]
            model.appendRow(items)

    def search_members(self, text: str, model: Any, limit: Optional[int] = None) -> int:
        """Query socios matching `text` and populate the provided model.

        Matches against numero_socio, nombre, apellidos and email,
        accent/case-insensitively. Empty `text` means "no filter" - every
        socio is returned (subject to `limit`), which is also how the
        default members table load (see MembersMenuView.load_table_view)
        gets its data.

        Args:
            text: Search text to filter members. Empty/None = no filter.
            model: Qt model to populate with results
            limit: Optional limit on number of rows to return

        Returns number of rows added.
        """
        if model is None:
            logger.warning("MembersMenuService.search_members: no model provided")
            return 0

        try:
            if limit == 0:
                limit = None

            rows = self._filter_socio_rows(self._fetch_socios_rows(), text)
            if limit is not None:
                rows = rows[:limit]

            self._populate_model(model, list(_SOCIO_COLUMNS), rows)
            logger.info(
                "MembersMenuService.search_members: %d rows for '%s' (limit: %s)", len(rows), text, limit
            )
            return len(rows)
        except Exception as exc:
            logger.exception("MembersMenuService.search_members: failed - %s", exc)
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
