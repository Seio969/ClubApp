"""Toolbar for the payment-methods table in the Settings screen."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .metodos_pago_service import MetodosPagoService
from .metodos_pago_dialog import MetodoPagoDialog
from utils.logger import get_logger

logger = get_logger(__name__)

# Column indices in the metodos_pago table model.
COL_ID = 0
COL_NOMBRE = 1
COL_ESTADO = 2
COL_TIPO = 3


class MetodosPagoToolBar(QToolBar):
    """Toolbar with Nuevo/Editar/Activar-Desactivar/Refrescar for MetodoPago."""

    def __init__(self, parent: Optional["QWidget"] = None, service: Optional[MetodosPagoService] = None) -> None:
        super().__init__(parent)
        self.setObjectName("metodosPagoToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None
        self.service: MetodosPagoService = service or MetodosPagoService()

        self._setup_actions()

    def _setup_actions(self) -> None:
        icon_new = self.style().standardIcon(QStyle.SP_FileIcon)
        act_new = self.addAction(icon_new, "Nuevo")
        act_new.setToolTip("Añadir un método de pago personalizado")
        act_new.triggered.connect(self.on_add_metodo)

        icon_edit = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        act_edit = self.addAction(icon_edit, "Editar")
        act_edit.setToolTip("Renombrar el método de pago seleccionado")
        act_edit.triggered.connect(self.on_edit_metodo)

        icon_toggle = self.style().standardIcon(QStyle.SP_DialogCancelButton)
        act_toggle = self.addAction(icon_toggle, "Activar/Desactivar")
        act_toggle.setToolTip("Alternar el estado del método de pago seleccionado")
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
                logger.exception("MetodosPagoToolBar: refresh_table failed - %s", exc)

    def on_add_metodo(self) -> None:
        dialog = MetodoPagoDialog(self)
        if dialog.exec() != MetodoPagoDialog.DialogCode.Accepted:
            return
        new_id = self.service.add_metodo_pago(dialog.get_nombre())
        if new_id is None:
            QMessageBox.critical(
                self, "Error", "No se pudo crear el método de pago. Puede que ya exista uno con ese nombre."
            )
            return
        self._refresh_parent()

    def on_edit_metodo(self) -> None:
        if self.model is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Editar método", "Seleccione un método de pago para editar.")
            return

        id_item = self.model.item(row, COL_ID)
        nombre_item = self.model.item(row, COL_NOMBRE)
        try:
            id_metodo = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_metodo = None
        nombre_actual = nombre_item.text() if nombre_item is not None else ""

        if id_metodo is None:
            logger.warning("MetodosPagoToolBar.on_edit_metodo: could not resolve id_metodo for row=%s", row)
            return
        if self.service.is_fixed(nombre_actual):
            QMessageBox.information(
                self,
                "Método fijo",
                "Los métodos de pago fijos (definidos por el club) no se pueden renombrar.",
            )
            return

        dialog = MetodoPagoDialog(self, initial_nombre=nombre_actual)
        if dialog.exec() != MetodoPagoDialog.DialogCode.Accepted:
            return

        if not self.service.rename_metodo_pago(id_metodo, dialog.get_nombre()):
            QMessageBox.critical(
                self, "Error", "No se pudo renombrar el método de pago. Puede que ya exista uno con ese nombre."
            )
            return
        self._refresh_parent()

    def on_toggle_estado(self) -> None:
        if self.model is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Activar/Desactivar", "Seleccione un método de pago.")
            return

        id_item = self.model.item(row, COL_ID)
        nombre_item = self.model.item(row, COL_NOMBRE)
        estado_item = self.model.item(row, COL_ESTADO)
        try:
            id_metodo = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_metodo = None
        if id_metodo is None:
            logger.warning("MetodosPagoToolBar.on_toggle_estado: could not resolve id_metodo for row=%s", row)
            return

        nombre = nombre_item.text() if nombre_item is not None else ""
        estado_actual = estado_item.text() if estado_item is not None else "activo"
        nuevo_estado = "inactivo" if estado_actual == "activo" else "activo"

        if nuevo_estado == "inactivo":
            reply = QMessageBox.question(
                self,
                "Confirmar desactivación",
                f"¿Desactivar el método de pago '{nombre}'?\n\nDejará de estar disponible para nuevos movimientos.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not self.service.set_metodo_pago_estado(id_metodo, nuevo_estado):
            QMessageBox.critical(self, "Error", "No se pudo actualizar el estado del método de pago.")
            return
        self._refresh_parent()

    def on_refresh(self) -> None:
        self._refresh_parent()
