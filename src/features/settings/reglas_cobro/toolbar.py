"""Toolbar for the billing-rules table in the Settings hub."""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .service import ReglasCobroService
from .dialog import ReglaCobroDialog
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

        icon_activate = self.style().standardIcon(QStyle.SP_DialogYesButton)
        act_activate = self.addAction(icon_activate, "Activar")
        act_activate.setToolTip("Activar las reglas de cobro seleccionadas")
        act_activate.triggered.connect(self.on_activate_reglas)

        icon_deactivate = self.style().standardIcon(QStyle.SP_DialogNoButton)
        act_deactivate = self.addAction(icon_deactivate, "Desactivar")
        act_deactivate.setToolTip("Desactivar las reglas de cobro seleccionadas")
        act_deactivate.triggered.connect(self.on_deactivate_reglas)

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
        if self.model is None or self.table is None:
            return
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Editar regla", "Seleccione una regla de cobro para editar.")
            return
        if len(sel) > 1:
            QMessageBox.information(
                self, "Editar regla", "Seleccione una única regla de cobro para editar."
            )
            return
        row = sel[0].row()

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

    def on_activate_reglas(self) -> None:
        self._set_estado_for_selection("activo")

    def on_deactivate_reglas(self) -> None:
        self._set_estado_for_selection("inactivo")

    def _resolve_selected_rows(self) -> List[Tuple[int, str, str]]:
        """Resolve every selected row to (id_regla, descripcion, estado_actual)."""
        if self.table is None or self.model is None:
            return []
        resolved: List[Tuple[int, str, str]] = []
        for index in self.table.selectionModel().selectedRows():
            row = index.row()
            id_item = self.model.item(row, COL_ID)
            descripcion_item = self.model.item(row, COL_DESCRIPCION)
            estado_item = self.model.item(row, COL_ESTADO)
            try:
                id_regla = int(id_item.text()) if id_item is not None else None
            except (ValueError, AttributeError):
                id_regla = None
            if id_regla is None:
                logger.warning("ReglasCobroToolBar: could not resolve id_regla for row=%s", row)
                continue
            descripcion = descripcion_item.text() if descripcion_item is not None else ""
            estado_actual = estado_item.text() if estado_item is not None else "activo"
            resolved.append((id_regla, descripcion, estado_actual))
        return resolved

    def _set_estado_for_selection(self, nuevo_estado: str) -> None:
        """Activate or deactivate every selected rule, in a single batch.

        Rows already in the target estado are left untouched (no-op) -
        e.g. selecting 3 activo + 1 inactivo rows and clicking "Desactivar"
        only changes the 3 activo ones (PLAN.md 1, decided).
        """
        if self.table is None or self.model is None:
            return
        titulo = "Activar" if nuevo_estado == "activo" else "Desactivar"
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, titulo, "Seleccione una o más reglas de cobro.")
            return

        targets = [
            (id_regla, descripcion)
            for id_regla, descripcion, estado_actual in self._resolve_selected_rows()
            if estado_actual != nuevo_estado
        ]
        if not targets:
            verbo = "activas" if nuevo_estado == "activo" else "inactivas"
            QMessageBox.information(self, titulo, f"Las reglas de cobro seleccionadas ya están {verbo}.")
            return

        if nuevo_estado == "inactivo" and not self._confirm_deactivation([descripcion for _, descripcion in targets]):
            return

        failures = [
            descripcion
            for id_regla, descripcion in targets
            if not self.service.set_regla_cobro_estado(id_regla, nuevo_estado)
        ]
        if failures:
            QMessageBox.critical(
                self, "Error", "No se pudo actualizar el estado de: " + ", ".join(failures)
            )
        self._refresh_parent()

    def _confirm_deactivation(self, names: List[str]) -> bool:
        if len(names) == 1:
            message = (
                f"¿Desactivar la regla de cobro '{names[0]}'?\n\n"
                "Dejará de estar disponible para nuevos movimientos."
            )
        else:
            listado = "\n".join(f"- {n}" for n in names)
            message = (
                f"¿Desactivar las siguientes {len(names)} reglas de cobro?\n\n{listado}\n\n"
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
