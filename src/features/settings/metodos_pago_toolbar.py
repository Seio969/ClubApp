"""Toolbar for the payment-methods table in the Settings screen."""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

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

        icon_activate = self.style().standardIcon(QStyle.SP_DialogYesButton)
        act_activate = self.addAction(icon_activate, "Activar")
        act_activate.setToolTip("Activar los métodos de pago seleccionados")
        act_activate.triggered.connect(self.on_activate_metodos)

        icon_deactivate = self.style().standardIcon(QStyle.SP_DialogNoButton)
        act_deactivate = self.addAction(icon_deactivate, "Desactivar")
        act_deactivate.setToolTip("Desactivar los métodos de pago seleccionados")
        act_deactivate.triggered.connect(self.on_deactivate_metodos)

        self.addSeparator()

        icon_refresh = self.style().standardIcon(QStyle.SP_BrowserReload)
        act_refresh = self.addAction(icon_refresh, "Refrescar")
        act_refresh.setToolTip("Refrescar lista")
        act_refresh.triggered.connect(self.on_refresh)

    def set_table_references(self, table: QTableView, model: QStandardItemModel) -> None:
        self.table = table
        self.model = model

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
        if self.model is None or self.table is None:
            return
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Editar método", "Seleccione un método de pago para editar.")
            return
        if len(sel) > 1:
            QMessageBox.information(
                self, "Editar método", "Seleccione un único método de pago para editar."
            )
            return
        row = sel[0].row()

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

    def on_activate_metodos(self) -> None:
        self._set_estado_for_selection("activo")

    def on_deactivate_metodos(self) -> None:
        self._set_estado_for_selection("inactivo")

    def _resolve_selected_rows(self) -> List[Tuple[int, str, str]]:
        """Resolve every selected row to (id_metodo, nombre, estado_actual)."""
        if self.table is None or self.model is None:
            return []
        resolved: List[Tuple[int, str, str]] = []
        for index in self.table.selectionModel().selectedRows():
            row = index.row()
            id_item = self.model.item(row, COL_ID)
            nombre_item = self.model.item(row, COL_NOMBRE)
            estado_item = self.model.item(row, COL_ESTADO)
            try:
                id_metodo = int(id_item.text()) if id_item is not None else None
            except (ValueError, AttributeError):
                id_metodo = None
            if id_metodo is None:
                logger.warning("MetodosPagoToolBar: could not resolve id_metodo for row=%s", row)
                continue
            nombre = nombre_item.text() if nombre_item is not None else ""
            estado_actual = estado_item.text() if estado_item is not None else "activo"
            resolved.append((id_metodo, nombre, estado_actual))
        return resolved

    def _set_estado_for_selection(self, nuevo_estado: str) -> None:
        """Activate or deactivate every selected method, in a single batch.

        Rows already in the target estado are left untouched (no-op) -
        e.g. selecting 3 activo + 1 inactivo rows and clicking "Desactivar"
        only changes the 3 activo ones (PLAN.md 1, decided).
        """
        if self.table is None or self.model is None:
            return
        titulo = "Activar" if nuevo_estado == "activo" else "Desactivar"
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, titulo, "Seleccione uno o más métodos de pago.")
            return

        targets = [
            (id_metodo, nombre)
            for id_metodo, nombre, estado_actual in self._resolve_selected_rows()
            if estado_actual != nuevo_estado
        ]
        if not targets:
            verbo = "activos" if nuevo_estado == "activo" else "inactivos"
            QMessageBox.information(self, titulo, f"Los métodos de pago seleccionados ya están {verbo}.")
            return

        if nuevo_estado == "inactivo" and not self._confirm_deactivation([nombre for _, nombre in targets]):
            return

        failures = [
            nombre for id_metodo, nombre in targets if not self.service.set_metodo_pago_estado(id_metodo, nuevo_estado)
        ]
        if failures:
            QMessageBox.critical(
                self, "Error", "No se pudo actualizar el estado de: " + ", ".join(failures)
            )
        self._refresh_parent()

    def _confirm_deactivation(self, names: List[str]) -> bool:
        if len(names) == 1:
            message = (
                f"¿Desactivar el método de pago '{names[0]}'?\n\n"
                "Dejará de estar disponible para nuevos movimientos."
            )
        else:
            listado = "\n".join(f"- {n}" for n in names)
            message = (
                f"¿Desactivar los siguientes {len(names)} métodos de pago?\n\n{listado}\n\n"
                "Dejarán de estar disponibles para nuevos movimientos."
            )
        reply = QMessageBox.question(
            self,
            "Confirmar desactivación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def on_refresh(self) -> None:
        self._refresh_parent()
