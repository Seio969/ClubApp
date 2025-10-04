"""Members toolbar component.

This module provides a specialized toolbar for the members view with
actions for creating, editing, deleting, refreshing, and exporting member data.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class MembersToolBar(QToolBar):
    """Toolbar for members view with CRUD and utility actions."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("membersToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        
        # Reference to the table view and model (will be set by parent)
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None
        
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

    def set_table_references(self, table: QTableView, model: QStandardItemModel) -> None:
        """Set references to the table view and model for toolbar operations."""
        self.table = table
        self.model = model

    def on_add_member(self) -> None:
        """Handle add member action."""
        # Placeholder: real implementation should open the member form
        print("Añadir miembro (placeholder)")

    def on_edit_member(self) -> None:
        """Handle edit member action."""
        if not self.table:
            print("Error: no hay referencia a la tabla")
            return
            
        # In a real app, check selection and open the selected member for edit
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            print("Editar: no hay ninguna fila seleccionada")
            return
        row = sel[0].row()
        if self.model:
            id_item = self.model.item(row, 0)
            print(f"Editar miembro (placeholder) id={id_item.text() if id_item else row}")
        else:
            print(f"Editar miembro (placeholder) fila={row}")

    def on_delete_member(self) -> None:
        """Handle delete member action."""
        if not self.table or not self.model:
            print("Error: no hay referencias a la tabla o modelo")
            return
            
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            print("Eliminar: no hay ninguna fila seleccionada")
            return
        # Remove selected rows from the model (simple behavior for demo)
        rows = sorted((s.row() for s in sel), reverse=True)
        for r in rows:
            self.model.removeRow(r)
        print(f"Eliminadas {len(rows)} fila(s)")

    def on_refresh(self) -> None:
        """Handle refresh action."""
        if not self.model:
            print("Error: no hay referencia al modelo")
            return
            
        # For demonstration, clear and re-add a small set of sample rows
        print("Refrescar lista (placeholder)")
        self.model.removeRows(0, self.model.rowCount())
        for i in range(1, 6):
            row = [
                QStandardItem(str(i)), 
                QStandardItem(f"Miembro {i}"), 
                QStandardItem(f"m{i}@example.com"), 
                QStandardItem("Activo")
            ]
            self.model.appendRow(row)

    def on_export(self) -> None:
        """Handle export action."""
        # Placeholder: wire this to a real exporter in utils/exporters.py later
        print("Exportar resultados (placeholder)")