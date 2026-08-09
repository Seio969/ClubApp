"""Click-to-sort behaviour for the members results table.

Extracted from MembersMenuView into a mixin: these methods are sorting
logic but stay tightly coupled to the owning view's table/model/state, so a
mixin avoids threading a dozen callbacks through a standalone helper.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem

from utils.logger import get_logger
from utils.text import normalize_for_match

logger = get_logger(__name__)


class TableSortMixin:
    """Adds 3-state (asc/desc/none) header-click sorting.

    Expects the including class to provide: self.table, self.model,
    self.search_input, self._sort_column, self._sort_order,
    self._current_view_name, self._last_search_text, self.load_table_view(),
    self.on_search(), self.refresh_table(), self.ensure_columns_fill().
    """

    # Handle tildes and accents in sorting and searching by normalizing
    # text values to a diacritic-free form and using that for comparisons.
    # ---------------------- sorting helpers -------------------------

    def _normalize_for_sort(self, value: str) -> str:
        """Return a lowercase, diacritic-free version of the string for sorting.

        This converts characters like 'á' -> 'a', 'ñ' -> 'n', etc., and
        performs a casefold to make comparisons case-insensitive. Delegates
        to utils.text.normalize_for_match, which MembersMenuService's DB
        search also uses, so sorting and searching stay accent-insensitive
        the same way.
        """
        return normalize_for_match(value)

    def _make_sort_key(self, raw: str):
        """Create a sort key that prefers numeric sorting when values look numeric.

        Returns a tuple where the first element is 0 for numeric values and 1
        for text values so numbers sort before text when mixed. The second
        element is the numeric value or the normalized text.
        """
        if raw is None:
            return (1, "")
        s = str(raw).strip()
        # Try integer first, then float
        try:
            ival = int(s)
            return (0, ival)
        except Exception:
            pass
        try:
            fval = float(s)
            return (0, fval)
        except Exception:
            pass
        # Fallback to normalized text
        return (1, self._normalize_for_sort(s))

    def _on_header_clicked(self, index: int) -> None:
        """Handle clicks on header sections to toggle sort state.

        Cycle: (no sort) -> ASC -> DESC -> (no sort)
        Clicking a different column restarts the cycle on that column.

        Always clears the current selection first (PLAN.md 4.4 decision:
        sorting never preserves the selected row, unlike a plain reload).
        """
        try:
            self.table.clearSelection()
            # Determine next state
            if self._sort_column is None or self._sort_column != index:
                # New column selected -> start with ascending
                self._sort_column = index
                self._sort_order = Qt.SortOrder.AscendingOrder
                self._apply_sort()
                return

            # Same column clicked again -> toggle
            if self._sort_order == Qt.SortOrder.AscendingOrder:
                self._sort_order = Qt.SortOrder.DescendingOrder
                self._apply_sort()
                return

            if self._sort_order == Qt.SortOrder.DescendingOrder:
                # Third click: clear sorting and restore original order
                self._clear_sort()
                return
        except Exception:
            logger.exception("TableSortMixin._on_header_clicked: sorting failed")

    def _apply_sort(self) -> None:
        """Apply the current sort to the model and show indicator."""
        if self._sort_column is None or self._sort_order is None:
            return
        try:
            col = self._sort_column
            ascending = self._sort_order == Qt.SortOrder.AscendingOrder

            # Extract all rows as lists of text values
            rows = []
            row_count = self.model.rowCount()
            col_count = self.model.columnCount()
            for r in range(row_count):
                vals = []
                for c in range(col_count):
                    item = self.model.item(r, c)
                    vals.append("") if item is None else vals.append(item.text())
                rows.append(vals)

            # Stable sort using keys that remove diacritics and prefer numeric ordering
            rows.sort(key=lambda rv: self._make_sort_key(rv[col]), reverse=not ascending)

            # Repopulate model preserving header labels
            # Capture headers
            headers = [self.model.headerData(c, Qt.Orientation.Horizontal) for c in range(col_count)]

            # Clear and rebuild
            self.model.removeRows(0, self.model.rowCount())
            self.model.setColumnCount(col_count)
            if headers:
                self.model.setHorizontalHeaderLabels([str(h) if h is not None else "" for h in headers])

            for vals in rows:
                items = [QStandardItem("" if v is None else str(v)) for v in vals]
                self.model.appendRow(items)

            header = self.table.horizontalHeader()
            header.setSortIndicator(self._sort_column, self._sort_order)
            header.setSortIndicatorShown(True)
            # After sorting and repopulating the model, ensure columns fill
            try:
                self.ensure_columns_fill()
            except Exception:
                pass
        except Exception:
            logger.exception("TableSortMixin._apply_sort: failed to apply sort")

    def _clear_sort(self) -> None:
        """Clear any active sort and restore original data order.

        Restoration strategy:
        - If a DB-backed view is loaded, re-run load_table_view to fetch original order.
        - Otherwise, re-run the last search (if any) to restore the previous dataset.
        """
        try:
            self._sort_column = None
            self._sort_order = None
            header = self.table.horizontalHeader()
            header.setSortIndicatorShown(False)

            # Restore data depending on current context
            if getattr(self, "_current_view_name", None):
                # reload current view from service (original order)
                try:
                    self.load_table_view()
                    return
                except Exception:
                    pass

            # No current view: if we have a last search text, re-run search
            if self._last_search_text is not None:
                try:
                    # on_search will repopulate model using remembered input
                    # but ensure the input field still contains the same text
                    self.search_input.setText(self._last_search_text)
                    self.on_search()
                    return
                except Exception:
                    pass

            # Fallback: refresh table which may load a default view
            try:
                self.refresh_table()
            except Exception:
                pass
        except Exception:
            logger.exception("TableSortMixin._clear_sort: failed to clear sort")

    def _maybe_reapply_sort(self) -> None:
        """Re-apply active sort after the model has been (re)populated.

        This is used after loading a view so user-visible sorting persists
        across reloads when appropriate.
        """
        if self._sort_column is None or self._sort_order is None:
            return
        # Ensure column exists in new model
        try:
            col_count = self.model.columnCount()
            if 0 <= self._sort_column < col_count:
                self._apply_sort()
            else:
                # Invalid for this model: clear sort state and hide indicator
                self._sort_column = None
                self._sort_order = None
                self.table.horizontalHeader().setSortIndicatorShown(False)
        except Exception:
            pass
