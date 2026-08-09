"""Row-selection persistence helper for results tables.

Every screen's load_table_view() rebuilds its QStandardItemModel from
scratch (removeRows/setRowCount(0) + appendRow for each row), which discards
whatever row the user had selected - the QItemSelectionModel's indexes no
longer point at anything once the rows they referred to are gone. These two
functions let a reload re-select "the same logical row" (matched by the
id-column text, which is always column 0 - id_socio/id_metodo/id_regla/
id_transaccion) instead of leaving the selection empty.

Domain-agnostic, same reuse pattern as column_fill.py: used directly by
Members, Transacciones, Métodos de pago and Reglas de cobro rather than
each screen reimplementing it.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QTableView
from PySide6.QtGui import QStandardItemModel


def capture_selected_id(table: QTableView, model: QStandardItemModel, id_column: int = 0) -> Optional[str]:
    """Return the id-column text of the currently selected row, if any.

    Call this before rebuilding `model` and pass the result to
    restore_selected_id() afterwards.
    """
    selection_model = table.selectionModel()
    if selection_model is None:
        return None
    rows = selection_model.selectedRows(id_column)
    if not rows:
        return None
    return rows[0].data()


def restore_selected_id(table: QTableView, model: QStandardItemModel, id_value: Optional[str], id_column: int = 0) -> None:
    """Re-select the row whose id-column text matches `id_value`, if present.

    No-ops if id_value is None or no row matches (the row was deleted, or a
    search/filter now excludes it) - the table is simply left unselected,
    same as any other reload.
    """
    if id_value is None:
        return
    for row in range(model.rowCount()):
        item = model.item(row, id_column)
        if item is not None and item.text() == id_value:
            table.selectRow(row)
            return
