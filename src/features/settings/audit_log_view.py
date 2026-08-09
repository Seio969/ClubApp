"""Registro de auditoría screen - one section reachable from the Settings
hub (PLAN.md 2.12). Read-only viewer over Log rows written by every write
service via database/audit.py's record_log() - no toolbar, no CRUD: Log
rows are a permanent audit trail, same append-only rule as Transaccion.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QStyle,
    QSizePolicy,
    QTableView,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QStandardItemModel
from PySide6.QtCore import Qt, QEvent, QTimer

from .audit_log_service import AuditLogService
from features.members.column_fill import ensure_columns_fill as _ensure_columns_fill
from features.members.table_sort import TableSortMixin
from features.members.table_selection import capture_selected_id, restore_selected_id
from ui.styles import SETTINGS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)

_TODAS = "Todas"


class AuditLogView(QWidget, TableSortMixin):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsMenu")
        self.main_window = parent
        self._service = AuditLogService()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top bar: back button (to the Settings hub) + screen title ---
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

        title = QLabel("Registro de auditoría")
        title.setObjectName("screenTitle")
        top_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        main_layout.addWidget(top_bar)

        # --- Filters bar: search, tabla filter, refrescar -----------------
        filters_bar = QWidget(self)
        filters_layout = QHBoxLayout(filters_bar)
        filters_layout.setContentsMargins(6, 0, 6, 0)

        self.search_input = QLineEdit(filters_bar)
        self.search_input.setPlaceholderText("Buscar por socio, acción o descripción...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.returnPressed.connect(self.on_search)
        filters_layout.addWidget(self.search_input, 1)

        # Live/incremental search (same debounce pattern as Members/
        # Transacciones, PLAN.md 4.5).
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(250)
        self._search_debounce_timer.timeout.connect(self.on_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)

        btn_search = QPushButton("Buscar", filters_bar)
        btn_search.clicked.connect(self.on_search)
        filters_layout.addWidget(btn_search)

        filters_layout.addSpacing(12)
        filters_layout.addWidget(QLabel("Tabla:", filters_bar))
        self.tabla_filter = QComboBox(filters_bar)
        self.tabla_filter.addItem(_TODAS, None)
        self.tabla_filter.currentIndexChanged.connect(self.on_search)
        filters_layout.addWidget(self.tabla_filter)

        filters_layout.addStretch(1)

        btn_refresh = QPushButton("Refrescar", filters_bar)
        btn_refresh.clicked.connect(self.refresh_table)
        filters_layout.addWidget(btn_refresh)

        main_layout.addWidget(filters_bar)

        # --- Table ---------------------------------------------------------
        self.table = QTableView(self)
        self.table.setObjectName("resultsTable")
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.model = QStandardItemModel(0, 7, self)
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self._on_header_clicked)

        self._sort_column = None
        self._sort_order = None
        self._last_search_text = None
        self._current_view_name = "logs"

        main_layout.addWidget(self.table)

        self.setStyleSheet(SETTINGS_MENU_STYLESHEET)

        self._populate_tabla_filter()
        try:
            self.load_table_view()
        except Exception:
            logger.exception("AuditLogView.__init__: initial load_table_view failed")

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
            logger.warning("AuditLogView.on_back_to_settings: no se pudo navegar a Ajustes")

    def _populate_tabla_filter(self) -> None:
        """Fill the tabla_afectada filter combo from whatever distinct
        values currently exist in logs, preserving the current selection
        when possible (called again on every Refrescar, not just at
        construction, since new tables can start appearing in logs)."""
        self.tabla_filter.blockSignals(True)
        current = self.tabla_filter.currentData()
        self.tabla_filter.clear()
        self.tabla_filter.addItem(_TODAS, None)
        for tabla in self._service.list_tablas_afectadas():
            self.tabla_filter.addItem(tabla, tabla)
        idx = self.tabla_filter.findData(current)
        self.tabla_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.tabla_filter.blockSignals(False)

    def _on_search_text_changed(self, _text: str) -> None:
        """Restart the debounce timer on every keystroke (PLAN.md 4.5)."""
        self._search_debounce_timer.start()

    def on_search(self) -> None:
        self._search_debounce_timer.stop()
        text = self.search_input.text().strip()
        self._last_search_text = text
        tabla = self.tabla_filter.currentData()

        selected_id = capture_selected_id(self.table, self.model)
        added = self._service.list_logs(text, tabla_afectada=tabla, model=self.model)
        logger.info("AuditLogView.on_search: %d rows (tabla_afectada=%s)", added, tabla)
        restore_selected_id(self.table, self.model, selected_id)

        try:
            self.ensure_columns_fill()
        except Exception:
            pass

    def load_table_view(self) -> None:
        """Reload logs with the current filters (used on first load and by
        TableSortMixin's sort-clear restoration)."""
        self.on_search()

    def refresh_table(self) -> None:
        try:
            self._populate_tabla_filter()
            self.load_table_view()
        except Exception as exc:
            logger.exception("AuditLogView.refresh_table: failed - %s", exc)


def show_audit_log_view(main_window) -> None:
    """Ensure an AuditLogView exists in the application's central stack and
    make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    av = getattr(main_window, "_audit_log_view", None)
    if av is None:
        av = AuditLogView(main_window)
        main_window._audit_log_view = av
        main_window._stack.addWidget(av)

    main_window._stack.setCurrentWidget(av)
