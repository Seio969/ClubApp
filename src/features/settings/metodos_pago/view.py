"""Métodos de pago screen - one section reachable from the Settings hub.

Unlike Members' screen, this table has a handful of rows at most (5 fixed
methods plus whatever custom ones the club adds), so there's no
search/sort composition here - just a table and a toolbar, per
UI_PROPOSAL.md's "small grids" guidance for this screen.
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

from .toolbar import MetodosPagoToolBar
from .service import MetodosPagoService
from features.members.column_fill import ensure_columns_fill as _ensure_columns_fill
from features.members.table_selection import capture_selected_id, restore_selected_id
from ui.styles import SETTINGS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = ["ID", "Nombre", "Estado", "Tipo"]


class MetodosPagoView(QWidget):
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

        title = QLabel("Métodos de pago")
        title.setObjectName("screenTitle")
        top_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        main_layout.addWidget(top_bar)

        # --- Toolbar -----------------------------------------------------
        self.toolbar = MetodosPagoToolBar(self)
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
        header.setDefaultSectionSize(140)
        header.setStretchLastSection(False)

        self.toolbar.set_table_references(self.table, self.model)
        self._service = MetodosPagoService()

        main_layout.addWidget(self.table)

        self.setStyleSheet(SETTINGS_MENU_STYLESHEET)

        try:
            self.load_table_view()
        except Exception:
            logger.exception("MetodosPagoView.__init__: initial load_table_view failed")

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
        """Return to the Settings hub (not the main menu directly - this
        screen is nested one level under Ajustes, same as any other
        settings section)."""
        if self.main_window and hasattr(self.main_window, "_stack") and hasattr(self.main_window, "_settings_view"):
            self.main_window._stack.setCurrentWidget(self.main_window._settings_view)
        else:
            logger.warning("MetodosPagoView.on_back_to_settings: no se pudo navegar a Ajustes")

    def load_table_view(self) -> None:
        """Reload the metodos_pago table from the database."""
        selected_id = capture_selected_id(self.table, self.model)
        metodos = self._service.list_metodos_pago()
        self.model.setRowCount(0)
        for metodo in metodos:
            row = [
                QStandardItem(str(metodo["id_metodo"])),
                QStandardItem(metodo["nombre"]),
                QStandardItem(metodo["estado"] or "activo"),
                QStandardItem("Fijo" if metodo["fijo"] else "Personalizado"),
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
            logger.exception("MetodosPagoView.refresh_table: failed - %s", exc)


def show_metodos_pago_view(main_window) -> None:
    """Ensure a MetodosPagoView exists in the application's central stack
    and make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    mv = getattr(main_window, "_metodos_pago_view", None)
    if mv is None:
        mv = MetodosPagoView(main_window)
        main_window._metodos_pago_view = mv
        main_window._stack.addWidget(mv)

    main_window._stack.setCurrentWidget(mv)
