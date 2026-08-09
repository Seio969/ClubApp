"""Reglas de cobro screen - one section reachable from the Settings hub.

Same "small grid, no search/límite/sort" shape as MetodosPagoView -
UI_PROPOSAL.md's guidance for this screen applies here too.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QSizePolicy,
    QTableView,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QEvent

from .reglas_cobro_toolbar import ReglasCobroToolBar
from .reglas_cobro_service import ReglasCobroService
from features.members.column_fill import ensure_columns_fill as _ensure_columns_fill
from features.members.table_selection import capture_selected_id, restore_selected_id
from ui.styles import SETTINGS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = ["ID", "Descripción", "Cuota mensual", "Plazo (días)", "Penalización", "Descuento", "Estado"]


class ReglasCobroView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsMenu")
        self.main_window = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top bar: back button (to the Settings hub) + screen title --
        top_bar = QWidget(self)
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 6, 6, 6)

        back_button = QPushButton("Volver")
        back_button.setObjectName("backButton")
        back_button.setToolTip("Volver a Ajustes")
        back_button.setMaximumWidth(120)
        back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        back_button.clicked.connect(self.on_back_to_settings)
        top_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Reglas de cobro")
        title.setObjectName("screenTitle")
        top_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        main_layout.addWidget(top_bar)

        # --- Toolbar -----------------------------------------------------
        self.toolbar = ReglasCobroToolBar(self)
        main_layout.addWidget(self.toolbar)

        # --- Table ---------------------------------------------------------
        self.table = QTableView(self)
        self.table.setObjectName("resultsTable")
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.model = QStandardItemModel(0, len(_HEADERS), self)
        self.model.setHorizontalHeaderLabels(_HEADERS)
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(False)

        self.toolbar.set_table_references(self.table, self.model)
        self._service = ReglasCobroService()

        main_layout.addWidget(self.table)

        self.setStyleSheet(SETTINGS_MENU_STYLESHEET)

        try:
            self.load_table_view()
        except Exception:
            logger.exception("ReglasCobroView.__init__: initial load_table_view failed")

        try:
            self.ensure_columns_fill()
        except Exception:
            pass

        self.table.viewport().installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is not None and ev.type() == QEvent.Type.Resize and obj is self.table.viewport():
            try:
                self.ensure_columns_fill()
            except Exception:
                pass
        return super().eventFilter(obj, ev)

    def hideEvent(self, event) -> None:
        """Clear the table selection whenever this screen stops being the
        current widget - see MembersMenuView.hideEvent (PLAN.md 4.4)."""
        self.table.clearSelection()
        super().hideEvent(event)

    def ensure_columns_fill(self) -> None:
        _ensure_columns_fill(self.table, self.model)

    def on_back_to_settings(self) -> None:
        if self.main_window and hasattr(self.main_window, "_stack") and hasattr(self.main_window, "_settings_view"):
            self.main_window._stack.setCurrentWidget(self.main_window._settings_view)
        else:
            logger.warning("ReglasCobroView.on_back_to_settings: no se pudo navegar a Ajustes")

    def load_table_view(self) -> None:
        """Reload the reglas_cobro table from the database."""
        selected_id = capture_selected_id(self.table, self.model)
        reglas = self._service.list_reglas_cobro()
        self.model.setRowCount(0)
        for regla in reglas:
            row = [
                QStandardItem(str(regla["id_regla"])),
                QStandardItem(regla["descripcion"] or ""),
                QStandardItem(_fmt(regla["cuota_mensual"])),
                QStandardItem(_fmt(regla["plazo_pago"])),
                QStandardItem(_fmt(regla["penalizacion"])),
                QStandardItem(_fmt(regla["descuento"])),
                QStandardItem(regla["estado"] or "activo"),
            ]
            for item in row:
                item.setEditable(False)
            self.model.appendRow(row)
        restore_selected_id(self.table, self.model, selected_id)
        try:
            self.ensure_columns_fill()
        except Exception:
            pass

    def refresh_table(self) -> None:
        try:
            self.load_table_view()
        except Exception as exc:
            logger.exception("ReglasCobroView.refresh_table: failed - %s", exc)


def _fmt(value) -> str:
    return "" if value is None else str(value)


def show_reglas_cobro_view(main_window) -> None:
    """Ensure a ReglasCobroView exists in the application's central stack
    and make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    rv = getattr(main_window, "_reglas_cobro_view", None)
    if rv is None:
        rv = ReglasCobroView(main_window)
        main_window._reglas_cobro_view = rv
        main_window._stack.addWidget(rv)

    main_window._stack.setCurrentWidget(rv)
