"""Toolbar for the standalone Transacciones screen.

Only Nuevo movimiento / Refrescar / Exportar (per UI_PROPOSAL.md's mockup)
- no Editar/Eliminar: once persisted, a transaction is part of the audit
trail. A correction is a new transaction (e.g. a reembolso), not an edit to
history, same spirit as the soft-deactivation-only pattern used elsewhere
in this app but stricter (no state to toggle back either).
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .dialog import TransactionDialog
from .service import TransactionsService
from utils.logger import get_logger

logger = get_logger(__name__)


class TransactionsToolBar(QToolBar):
    """Toolbar with Nuevo movimiento/Refrescar/Exportar for Transaccion."""

    def __init__(self, parent: Optional["QWidget"] = None, service: Optional[TransactionsService] = None) -> None:
        super().__init__(parent)
        self.setObjectName("transactionsToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None
        self.service: TransactionsService = service or TransactionsService()

        self._setup_actions()

    def _setup_actions(self) -> None:
        icon_new = self.style().standardIcon(QStyle.SP_FileIcon)
        act_new = self.addAction(icon_new, "Nuevo movimiento")
        act_new.setToolTip("Registrar un cargo, pago o reembolso")
        act_new.triggered.connect(self.on_add_transaction)

        self.addSeparator()

        icon_refresh = self.style().standardIcon(QStyle.SP_BrowserReload)
        act_refresh = self.addAction(icon_refresh, "Refrescar")
        act_refresh.setToolTip("Refrescar lista")
        act_refresh.triggered.connect(self.on_refresh)

        icon_export = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        act_export = self.addAction(icon_export, "Exportar")
        act_export.setToolTip("Exportar resultados")
        act_export.triggered.connect(self.on_export)

    def set_table_references(self, table: QTableView, model: QStandardItemModel) -> None:
        self.table = table
        self.model = model

    def _refresh_parent(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
            except Exception as exc:
                logger.exception("TransactionsToolBar: refresh_table failed - %s", exc)

    def on_add_transaction(self) -> None:
        dialog = TransactionDialog(self, service=self.service)
        if dialog.exec() != TransactionDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        error = self.service.validate_transaction(data)
        if error:
            QMessageBox.warning(self, "Movimiento no válido", error)
            return

        new_id = self.service.add_transaction(data)
        if new_id is None:
            QMessageBox.critical(
                self, "Error", "No se pudo registrar el movimiento. Revise los datos e inténtelo de nuevo."
            )
            return
        self._refresh_parent()

    def on_refresh(self) -> None:
        self._refresh_parent()

    def on_export(self) -> None:
        rows: list[list[str]] = []
        if self.model is not None:
            for r in range(self.model.rowCount()):
                row_vals = []
                for c in range(self.model.columnCount()):
                    item = self.model.item(r, c)
                    row_vals.append(item.text() if item is not None else "")
                rows.append(row_vals)
        self.service.export_transactions(rows, destination=None)
