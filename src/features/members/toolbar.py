"""Members toolbar component.

This module provides a specialized toolbar for the members view with
actions for creating, editing, deleting, refreshing, and exporting member data.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .toolbar_service import MembersService
from .dialog import MemberDialog
from utils.logger import get_logger
logger = get_logger(__name__)


class MembersToolBar(QToolBar):
    """Toolbar for members view with CRUD and utility actions."""

    def __init__(self, parent: Optional[QWidget] = None, service: Optional[MembersService] = None) -> None:
        super().__init__(parent)
        self.setObjectName("membersToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        # Reference to the table view and model (will be set by parent)
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None

        # Behaviour service (non-UI logic)
        self.service: MembersService = service or MembersService()

        self._setup_actions()

    def _setup_actions(self) -> None:
        """Create and add all toolbar actions."""
        # New / Add action
        icon_new = self.style().standardIcon(QStyle.SP_FileIcon)
        act_new = self.addAction(icon_new, "Nuevo")
        act_new.setToolTip("Crear nuevo miembro")
        act_new.triggered.connect(self.on_add_member)

        # Edit action
        icon_edit = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        act_edit = self.addAction(icon_edit, "Editar")
        act_edit.setToolTip("Editar miembro seleccionado")
        act_edit.triggered.connect(self.on_edit_member)

        # Delete action
        icon_delete = self.style().standardIcon(QStyle.SP_TrashIcon)
        act_delete = self.addAction(icon_delete, "Eliminar")
        act_delete.setToolTip("Eliminar miembro seleccionado")
        act_delete.triggered.connect(self.on_delete_member)

        self.addSeparator()

        # Refresh
        icon_refresh = self.style().standardIcon(QStyle.SP_BrowserReload)
        act_refresh = self.addAction(icon_refresh, "Refrescar")
        act_refresh.setToolTip("Refrescar lista")
        act_refresh.triggered.connect(self.on_refresh)

        # Export
        icon_export = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        act_export = self.addAction(icon_export, "Exportar")
        act_export.setToolTip("Exportar resultados")
        act_export.triggered.connect(self.on_export)
        
        # Registrar cargos, pagos y reembolsos (placeholder for future behaviour)
        icon_register = self.style().standardIcon(QStyle.SP_DialogOpenButton)
        act_register = self.addAction(icon_register, "Registrar")
        act_register.setToolTip("Registrar cargos, pagos y devoluciones")
        act_register.triggered.connect(self.on_register_movements)

    def set_table_references(self, table: QTableView, model: QStandardItemModel) -> None:
        """Set references to the table view and model for toolbar operations."""
        self.table = table
        self.model = model

    def on_add_member(self) -> None:
        """Open the new-member dialog and persist the result to the DB."""
        dialog = MemberDialog(self)
        if dialog.exec() != MemberDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        new_id = self.service.add_member(data)
        if new_id is None:
            QMessageBox.critical(
                self, "Error", "No se pudo crear el miembro. Revise los datos e inténtelo de nuevo."
            )
            return

        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
            except Exception as exc:
                logger.exception("MembersToolBar.on_add_member: refresh_table failed - %s", exc)

    def on_edit_member(self) -> None:
        """Open the edit-member dialog pre-filled with the selected member's data."""
        if self.table is None or self.model is None:
            return
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Editar miembro", "Seleccione un miembro para editar.")
            return

        row = sel[0].row()
        id_item = self.model.item(row, 0)
        try:
            id_socio = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_socio = None
        if id_socio is None:
            logger.warning("MembersToolBar.on_edit_member: could not resolve id_socio for row=%s", row)
            return

        data = self.service.get_member(id_socio)
        if data is None:
            QMessageBox.critical(self, "Error", "No se pudo cargar el miembro seleccionado.")
            return

        dialog = MemberDialog(self, initial_data=data)
        if dialog.exec() != MemberDialog.DialogCode.Accepted:
            return

        if not self.service.update_member(id_socio, dialog.get_data()):
            QMessageBox.critical(
                self, "Error", "No se pudo actualizar el miembro. Revise los datos e inténtelo de nuevo."
            )
            return

        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
            except Exception as exc:
                logger.exception("MembersToolBar.on_edit_member: refresh_table failed - %s", exc)

    def on_delete_member(self) -> None:
        """Handle delete member action (deactivates the member, never a physical delete)."""
        if self.table is None:
            self.service.delete_members([])
            return
        sel = self.table.selectionModel().selectedRows()
        indices = [s.row() for s in sel] if sel else []

        def model_getter(row: int, col: int):
            if self.model is None:
                return None
            return self.model.item(row, col)

        rows_to_remove = self.service.delete_members(indices, model_getter)
        # Rows returned here were already deactivated (estado="inactivo") in
        # the database; remove them from the in-memory model for immediate
        # feedback.
        if self.model is not None and rows_to_remove:
            for r in rows_to_remove:
                self.model.removeRow(r)

    def on_refresh(self) -> None:
        """Handle refresh action."""
        # If the parent view provides a refresh_table method prefer that so
        # the UI reloads the actual DB-backed view. If not available, do
        # nothing (avoid inserting demo/sample rows).
        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
                return
            except Exception as exc:
                logger.exception("MembersToolBar.on_refresh: parent.refresh_table failed - %s", exc)

        # No parent refresh available. Previously we fell back to a
        # sample-data helper; that behaviour populated demo rows which is
        # undesirable. Keep this a no-op and let callers provide a proper
        # refresh_table implementation on the parent view.
        logger.info("MembersToolBar.on_refresh: no parent.refresh_table available - nothing to refresh")

    def on_export(self) -> None:
        """Handle export action."""
        # Extract plain rows from the model and pass to service
        rows: list[list[str]] = []
        if self.model is not None:
            for r in range(self.model.rowCount()):
                row_vals = []
                for c in range(self.model.columnCount()):
                    item = self.model.item(r, c)
                    try:
                        row_vals.append(item.text() if item is not None else "")
                    except Exception:
                        row_vals.append(str(item) if item is not None else "")
                rows.append(row_vals)
        self.service.export_members(rows, destination=None)

    def on_register_movements(self) -> None:
        """Handle register movements action (cargos / pagos / devoluciones).

        Currently a placeholder that delegates to the service layer. The
        service will implement detailed dialogs and persistence in the future.
        """
        if self.table is None:
            self.service.register_transactions([])
            return
        sel = self.table.selectionModel().selectedRows()
        indices = [s.row() for s in sel] if sel else []
        self.service.register_transactions(indices)