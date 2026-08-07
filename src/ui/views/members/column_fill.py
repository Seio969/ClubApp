"""Column-width helper for the members results table.

Extracted from MembersMenuView so the width-distribution algorithm can be
read/tested on its own, separate from widget construction and sorting.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTableView
from PySide6.QtGui import QStandardItemModel


def ensure_columns_fill(table: QTableView, model: QStandardItemModel) -> None:
    """Expand visible columns to fill available viewport width.

    Keeps the header's Interactive resize mode (user-draggable) rather than
    switching to Qt's Stretch mode, which would disable interactive resize.
    """
    header = table.horizontalHeader()
    if model is None:
        return
    col_count = model.columnCount()
    if col_count <= 0:
        return

    avail = table.viewport().width()
    visible_cols = [c for c in range(col_count) if not table.isColumnHidden(c)]
    if not visible_cols:
        return

    total = sum(header.sectionSize(c) for c in visible_cols)
    if total >= avail or total == 0:
        if total == 0:
            default = header.defaultSectionSize()
            for c in visible_cols:
                header.resizeSection(c, default)
        return

    extra = avail - total
    allocated = 0
    for i, c in enumerate(visible_cols):
        if i == len(visible_cols) - 1:
            inc = extra - allocated
        else:
            size = header.sectionSize(c)
            share = size / total if total > 0 else 1.0 / len(visible_cols)
            inc = int(round(share * extra))
            allocated += inc
        header.resizeSection(c, header.sectionSize(c) + inc)
