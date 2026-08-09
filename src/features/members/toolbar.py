"""Members toolbar component.

This module provides a specialized toolbar for the members view with
actions for creating, editing, activating/deactivating, refreshing, and
exporting member data.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

from PySide6.QtWidgets import QToolBar, QStyle, QTableView, QMessageBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from .toolbar_service import MembersService
from .dialog import MemberDialog
from features.transactions.dialog import TransactionDialog
from features.transactions.service import TransactionsService
from utils.logger import get_logger
logger = get_logger(__name__)

# Column indices in the members table model (see MembersMenuService's
# _SOCIO_COLUMNS - id_socio/numero_socio/nombre/apellidos/.../estado/...).
COL_ID = 0
COL_NOMBRE = 2
COL_APELLIDOS = 3
COL_ESTADO = 7


class MembersToolBar(QToolBar):
    """Toolbar for members view with CRUD and utility actions."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        service: Optional[MembersService] = None,
        transactions_service: Optional[TransactionsService] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("membersToolBar")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        # Reference to the table view and model (will be set by parent)
        self.table: Optional[QTableView] = None
        self.model: Optional[QStandardItemModel] = None

        # Behaviour services (non-UI logic)
        self.service: MembersService = service or MembersService()
        self.transactions_service: TransactionsService = transactions_service or TransactionsService()

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

        # Activate / deactivate (soft-delete) actions - same
        # Activar/Desactivar pattern as MetodosPagoToolBar/ReglasCobroToolBar.
        icon_activate = self.style().standardIcon(QStyle.SP_DialogYesButton)
        act_activate = self.addAction(icon_activate, "Activar")
        act_activate.setToolTip("Activar los miembros seleccionados")
        act_activate.triggered.connect(self.on_activate_members)

        icon_deactivate = self.style().standardIcon(QStyle.SP_DialogNoButton)
        act_deactivate = self.addAction(icon_deactivate, "Desactivar")
        act_deactivate.setToolTip("Desactivar los miembros seleccionados")
        act_deactivate.triggered.connect(self.on_deactivate_members)

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
        if not self._confirm_titular_swap(data.get("numero_socio"), data.get("es_titular"), exclude_id_socio=None):
            return
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
        if len(sel) > 1:
            QMessageBox.information(
                self, "Editar miembro", "Seleccione un único miembro para editar."
            )
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

        new_data = dialog.get_data()
        if not self._confirm_titular_swap(new_data.get("numero_socio"), new_data.get("es_titular"), exclude_id_socio=id_socio):
            return
        if not self.service.update_member(id_socio, new_data):
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

    def on_activate_members(self) -> None:
        self._set_estado_for_selection("activo")

    def on_deactivate_members(self) -> None:
        self._set_estado_for_selection("inactivo")

    def _resolve_selected_rows(self) -> List[Tuple[int, str, str]]:
        """Resolve every selected row to (id_socio, nombre_completo, estado_actual)."""
        if self.table is None or self.model is None:
            return []
        resolved: List[Tuple[int, str, str]] = []
        for index in self.table.selectionModel().selectedRows():
            row = index.row()
            id_item = self.model.item(row, COL_ID)
            nombre_item = self.model.item(row, COL_NOMBRE)
            apellidos_item = self.model.item(row, COL_APELLIDOS)
            estado_item = self.model.item(row, COL_ESTADO)
            try:
                id_socio = int(id_item.text()) if id_item is not None else None
            except (ValueError, AttributeError):
                id_socio = None
            if id_socio is None:
                logger.warning("MembersToolBar: could not resolve id_socio for row=%s", row)
                continue
            parts = [item.text() for item in (nombre_item, apellidos_item) if item is not None and item.text()]
            nombre_completo = " ".join(parts).strip() or f"fila {row}"
            estado_actual = estado_item.text() if estado_item is not None else "activo"
            resolved.append((id_socio, nombre_completo, estado_actual))
        return resolved

    def _set_estado_for_selection(self, nuevo_estado: str) -> None:
        """Activate or deactivate every selected member, in a single batch.

        Rows already in the target estado are left untouched (no-op) - same
        rule as ReglasCobroToolBar/MetodosPagoToolBar's
        _set_estado_for_selection. Never a physical delete - just
        estado="inactivo"/"activo" - but deactivating still asks for
        confirmation first (PLAN.md 2.2/4.4).
        """
        if self.table is None or self.model is None:
            return
        titulo = "Activar" if nuevo_estado == "activo" else "Desactivar"
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, titulo, "Seleccione uno o más miembros.")
            return

        targets = [
            (id_socio, nombre)
            for id_socio, nombre, estado_actual in self._resolve_selected_rows()
            if estado_actual != nuevo_estado
        ]
        if not targets:
            verbo = "activos" if nuevo_estado == "activo" else "inactivos"
            QMessageBox.information(self, titulo, f"Los miembros seleccionados ya están {verbo}.")
            return

        if nuevo_estado == "inactivo" and not self._confirm_deactivation([nombre for _, nombre in targets]):
            return

        failures = [
            nombre for id_socio, nombre in targets if not self.service.set_socio_estado(id_socio, nuevo_estado)
        ]
        if failures:
            QMessageBox.critical(
                self, "Error", "No se pudo actualizar el estado de: " + ", ".join(failures)
            )
        self._refresh_parent()

    def _confirm_deactivation(self, names: List[str]) -> bool:
        """Ask the user to confirm deactivating the given members by name.

        Never a physical delete - just estado="inactivo" - but it persists
        to the real DB, so it's worth a confirmation step before it fires
        (PLAN.md 2.2/4.4).
        """
        if len(names) == 1:
            message = f"¿Desactivar a {names[0]}?\n\nEl miembro se marcará como inactivo; su historial no se elimina."
        else:
            listado = "\n".join(f"- {n}" for n in names)
            message = (
                f"¿Desactivar los siguientes {len(names)} miembros?\n\n{listado}\n\n"
                "Se marcarán como inactivos; su historial no se elimina."
            )

        reply = QMessageBox.question(
            self,
            "Confirmar desactivación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _refresh_parent(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_table"):
            try:
                parent.refresh_table()
            except Exception as exc:
                logger.exception("MembersToolBar: refresh_table failed - %s", exc)

    def _confirm_titular_swap(
        self, numero_socio: Optional[str], wants_titular: bool, exclude_id_socio: Optional[int]
    ) -> bool:
        """Warn and ask for confirmation before a save would replace an
        existing titular for numero_socio with a different one (PLAN.md
        2.17). Returns True if the save should proceed - no existing
        titular, the existing titular *is* the row being saved, or the
        user confirmed the swap - False if the user declined.
        """
        if not wants_titular or not numero_socio:
            return True
        previous = self.service.get_titular(numero_socio)
        if previous is None:
            return True
        if exclude_id_socio is not None and previous.get("id_socio") == exclude_id_socio:
            return True
        nombre_previo = f"{previous.get('nombre', '')} {previous.get('apellidos', '')}".strip()
        reply = QMessageBox.question(
            self,
            "Confirmar cambio de titular",
            f"¿Reemplazar a {nombre_previo or 'el titular actual'} como titular del número "
            f"{numero_socio}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

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
        """Open TransactionDialog to register a Cargo/Pago/Reembolso/Devolución.

        This is the member-scoped shortcut decided in PLAN.md 2.4 (the
        "both entry points" navigation model): with exactly one member row
        selected, the dialog opens pre-filled and locked to that member
        (`preset_socio`); with none selected, it opens with the socio field
        open for search/select instead. Selecting more than one row is
        refused - same single-row-only rule as on_edit_member - since a
        movement is registered against one socio at a time.
        """
        preset_socio = None
        if self.table is not None and self.model is not None:
            sel = self.table.selectionModel().selectedRows()
            if len(sel) > 1:
                QMessageBox.information(
                    self, "Registrar movimiento", "Seleccione un único miembro, o ninguno para elegir el socio en el diálogo."
                )
                return
            if len(sel) == 1:
                row = sel[0].row()
                preset_socio = self._resolve_preset_socio(row)
                if preset_socio is None:
                    QMessageBox.critical(self, "Error", "No se pudo resolver el socio seleccionado.")
                    return
                if not self.transactions_service.has_titular(preset_socio["numero_socio"]):
                    QMessageBox.information(
                        self,
                        "Registrar movimiento",
                        f"El número de socio {preset_socio['numero_socio']} no tiene titular asignado. "
                        "Asigne un titular en Miembros antes de registrar movimientos.",
                    )
                    return

        dialog = TransactionDialog(self, service=self.transactions_service, preset_socio=preset_socio)
        if dialog.exec() != TransactionDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        error = self.transactions_service.validate_transaction(data)
        if error:
            QMessageBox.warning(self, "Movimiento no válido", error)
            return

        new_id = self.transactions_service.add_transaction(data)
        if new_id is None:
            QMessageBox.critical(
                self, "Error", "No se pudo registrar el movimiento. Revise los datos e inténtelo de nuevo."
            )
            return
        QMessageBox.information(self, "Movimiento registrado", "El movimiento se registró correctamente.")

    def _resolve_preset_socio(self, row: int) -> Optional[dict]:
        """Read the Members table's columns 0-3 for `row` into a preset_socio
        dict shaped like TransactionsService.list_socios_activos()'s rows.

        Column order matches MembersMenuService._SOCIO_COLUMNS: id_socio(0),
        numero_socio(1), nombre(2), apellidos(3).
        """
        if self.model is None:
            return None
        id_item = self.model.item(row, 0)
        numero_item = self.model.item(row, 1)
        nombre_item = self.model.item(row, 2)
        apellidos_item = self.model.item(row, 3)
        try:
            id_socio = int(id_item.text()) if id_item is not None else None
        except (ValueError, AttributeError):
            id_socio = None
        numero_socio = numero_item.text() if numero_item is not None else None
        if id_socio is None or not numero_socio:
            return None
        return {
            "id_socio": id_socio,
            "numero_socio": numero_socio,
            "nombre": nombre_item.text() if nombre_item is not None else "",
            "apellidos": apellidos_item.text() if apellidos_item is not None else "",
        }