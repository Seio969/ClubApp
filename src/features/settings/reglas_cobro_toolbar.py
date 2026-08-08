"""Toolbar for the billing-rules table in the Settings hub."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .reglas_cobro_service import ReglasCobroService
from .reglas_cobro_dialog import ReglaCobroDialog
from utils.logger import get_logger

logger = get_logger(__name__)

# Column indices in the reglas_cobro table model.
COL_ID = 0
COL_DESCRIPCION = 1
COL_ESTADO = 6


class ReglasCobroToolBar(QToolBar):
    """Toolbar with Nuevo/Editar/Activar-Desactivar/Refrescar for ReglaCobro."""

    def __init__(self, parent: Optional["QWidget"] = None, service: Optional[ReglasCobroService] = None) -> None:
        super().__init__(parent)
        self.setObjectName("reglasCobroToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None
        self.service: ReglasCobroService = service or ReglasCobroService()

        self._setup_actions()

    def _setup_actions(self) -> None:
        icon_new = self.style().standardIcon(QStyle.SP_FileIcon)
        act_new = self.addAction(icon_new, "Nueva")
        act_new.setToolTip("Añadir una nueva regla de cobro")
        act_new.triggered.connect(self.on_add_regla)

        icon_edit = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        act_edit = self.addAction(icon_edit, "Editar")
        act_edit.setToolTip("Editar la regla de cobro seleccionada")
        act_edit.triggered.connect(self.on_edit_regla)

        icon_toggle = self.style().standardIcon(QStyle.SP_DialogCancelButton)
        act_toggle = self.addAction(icon_toggle, "Activar/Desactivar")
        act_toggle.setToolTip("Alternar el estado de la regla de cobro seleccionada")
        act_toggle.triggered.connect(self.on_toggle_estado)

        self.addSeparator()

        icon_refresh = self.style().standardIcon(QStyle.SP_BrowserReload)
        act_refresh = self.addAction(icon_refresh, "Refrescar")
        act_refresh.setToolTip("Refrescar lista")
        act_refresh.triggered.connect(self.on_refresh)

    def set_table_references(self, table: QTableView, model: QStandardItemModel) -> None:
        self.table = table
        self.model = model

    def _selected_row(self) -> Optional[int]:
        if self.table is None:
            return None
        sel = self.table.selectionModel().selectedRows()
        return sel[0].row() if sel else None

    def _refresh_parent(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
            except Exception as exc:
                logger.exception("ReglasCobroToolBar: refresh_table failed - %s", exc)

    def on_add_regla(self) -> None:
        dialog = ReglaCobroDialog(self)
        if dialog.exec() != ReglaCobroDialog.DialogCode.Accepted:
            return
        new_id = self.service.add_regla_cobro(dialog.get_data())
        if new_id is None:
            QMessageBox.critical(self, "Error", "No se pudo crear la regla de cobro.")
            return
        self._refresh_parent()

    def on_edit_regla(self) -> None:
        if self.model is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Editar regla", "Seleccione una regla de cobro para editar.")
            return

        id_item = self.model.item(row, COL_ID)
        try:
            id_regla = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_regla = None
        if id_regla is None:
            logger.warning("ReglasCobroToolBar.on_edit_regla: could not resolve id_regla for row=%s", row)
            return

        data = self.service.get_regla_cobro(id_regla)
        if data is None:
            QMessageBox.critical(self, "Error", "No se pudo cargar la regla de cobro seleccionada.")
            return

        dialog = ReglaCobroDialog(self, initial_data=data)
        if dialog.exec() != ReglaCobroDialog.DialogCode.Accepted:
            return

        if not self.service.update_regla_cobro(id_regla, dialog.get_data()):
            QMessageBox.critical(self, "Error", "No se pudo actualizar la regla de cobro.")
            return
        self._refresh_parent()

    def on_toggle_estado(self) -> None:
        if self.model is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Activar/Desactivar", "Seleccione una regla de cobro.")
            return

        id_item = self.model.item(row, COL_ID)
        descripcion_item = self.model.item(row, COL_DESCRIPCION)
        estado_item = self.model.item(row, COL_ESTADO)
        try:
            id_regla = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_regla = None
        if id_regla is None:
            logger.warning("ReglasCobroToolBar.on_toggle_estado: could not resolve id_regla for row=%s", row)
            return

        descripcion = descripcion_item.text() if descripcion_item is not None else ""
        estado_actual = estado_item.text() if estado_item is not None else "activo"
        nuevo_estado = "inactivo" if estado_actual == "activo" else "activo"

        if nuevo_estado == "inactivo":
            reply = QMessageBox.question(
                self,
                "Confirmar desactivación",
                f"¿Desactivar la regla de cobro '{descripcion}'?\n\nDejará de estar disponible para nuevos movimientos.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not self.service.set_regla_cobro_estado(id_regla, nuevo_estado):
            QMessageBox.critical(self, "Error", "No se pudo actualizar el estado de la regla de cobro.")
            return
        self._refresh_parent()

    def on_refresh(self) -> None:
        self._refresh_parent()
