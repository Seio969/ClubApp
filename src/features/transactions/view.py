"""Standalone Transacciones screen (PLAN.md 2.4, "both entry points"
navigation model - see the Members-toolbar "Registrar" shortcut in
features/members/toolbar.py for the other one).

Club-wide browsing/filtering by socio (search), tipo, and período - the
README's "Filtrar transacciones por fecha, tipo o estado" requirement.
"Estado" is interpreted here as the período's estado (abierto/cerrado):
Transaccion itself has no estado column in models.py (db.sql's copy does,
but CLAUDE.md's schema-drift note says db.sql is stale and not a source of
truth - see models.py). Selecting a período already surfaces its estado in
the dropdown label; "fecha" filtering is column-click sortable, same
TableSortMixin used by Members, rather than a separate date-range control.
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
from PySide6.QtCore import Qt, QEvent

from .toolbar import TransactionsToolBar
from .service import TIPOS_TRANSACCION, TransactionsService
from features.members.column_fill import ensure_columns_fill as _ensure_columns_fill
from features.members.table_sort import TableSortMixin
from ui.styles import MEMBERS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)

_TODOS = "Todos"


class TransactionsView(QWidget, TableSortMixin):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("membersMenu")  # reuse Members' paper/table QSS root
        self.main_window = parent
        self._service = TransactionsService()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top bar: back, search, tipo filter, período filter ----------
        top_bar = QWidget(self)
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 6, 6, 6)

        back_button = QPushButton("Volver")
        back_button.setObjectName("backButton")
        back_button.setToolTip("Volver al menú principal")
        back_button.setMaximumWidth(120)
        back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        back_button.clicked.connect(self.on_back_to_main_menu)
        top_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.search_input = QLineEdit(top_bar)
        self.search_input.setPlaceholderText("Buscar por socio...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(220)
        self.search_input.returnPressed.connect(self.on_search)
        top_layout.addWidget(self.search_input, 1)

        btn_search = QPushButton("Buscar", top_bar)
        btn_search.clicked.connect(self.on_search)
        top_layout.addWidget(btn_search)

        top_layout.addSpacing(12)
        top_layout.addWidget(QLabel("Tipo:", top_bar))
        self.tipo_filter = QComboBox(top_bar)
        self.tipo_filter.addItem(_TODOS, None)
        for tipo in TIPOS_TRANSACCION:
            self.tipo_filter.addItem(tipo, tipo)
        self.tipo_filter.currentIndexChanged.connect(self.on_search)
        top_layout.addWidget(self.tipo_filter)

        top_layout.addSpacing(12)
        top_layout.addWidget(QLabel("Período:", top_bar))
        self.periodo_filter = QComboBox(top_bar)
        self.periodo_filter.currentIndexChanged.connect(self.on_search)
        top_layout.addWidget(self.periodo_filter)

        main_layout.addWidget(top_bar)

        # --- Toolbar -----------------------------------------------------
        self.toolbar = TransactionsToolBar(self, service=self._service)
        main_layout.addWidget(self.toolbar)

        # --- Table ---------------------------------------------------------
        self.table = QTableView(self)
        self.table.setObjectName("resultsTable")
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.model = QStandardItemModel(0, 8, self)
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
        self._current_view_name = "transacciones"

        self.toolbar.set_table_references(self.table, self.model)

        main_layout.addWidget(self.table)

        self.setStyleSheet(MEMBERS_MENU_STYLESHEET)

        self._populate_periodo_filter()
        try:
            self.load_table_view()
        except Exception:
            logger.exception("TransactionsView.__init__: initial load_table_view failed")

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

    def ensure_columns_fill(self) -> None:
        _ensure_columns_fill(self.table, self.model)

    def on_back_to_main_menu(self) -> None:
        if self.main_window and hasattr(self.main_window, "_stack") and hasattr(self.main_window, "_home"):
            self.main_window._stack.setCurrentWidget(self.main_window._home)
        else:
            logger.warning("TransactionsView.on_back_to_main_menu: no se pudo navegar al menú principal")

    def _populate_periodo_filter(self, select_id: Optional[int] = None) -> None:
        """Fill the período filter combo, defaulting to the currently open
        período (most recently started "abierto" one) when `select_id` isn't
        given and one exists - PLAN.md 2.4's decided default-filter.
        """
        self.periodo_filter.blockSignals(True)
        self.periodo_filter.clear()
        self.periodo_filter.addItem(_TODOS, None)
        periodos = self._service.list_periodos()
        select_index = 0
        default_abierto_index = None
        for idx, periodo in enumerate(periodos, start=1):
            self.periodo_filter.addItem(f"{periodo['nombre']} ({periodo['estado']})", periodo["id_periodo"])
            if select_id is not None and periodo["id_periodo"] == select_id:
                select_index = idx
            elif default_abierto_index is None and periodo["estado"] == "abierto":
                default_abierto_index = idx
        if select_id is None and default_abierto_index is not None:
            select_index = default_abierto_index
        self.periodo_filter.setCurrentIndex(select_index)
        self.periodo_filter.blockSignals(False)

    def on_search(self) -> None:
        text = self.search_input.text().strip()
        self._last_search_text = text
        tipo = self.tipo_filter.currentData()
        id_periodo = self.periodo_filter.currentData()
        added = self._service.list_transactions(text, tipo=tipo, id_periodo=id_periodo, model=self.model)
        logger.info("TransactionsView.on_search: %d rows (tipo=%s, id_periodo=%s)", added, tipo, id_periodo)
        try:
            self.ensure_columns_fill()
        except Exception:
            pass

    def load_table_view(self) -> None:
        """Reload transacciones with the current filters (used on first load
        and by TableSortMixin's sort-clear restoration).
        """
        self.on_search()

    def refresh_table(self) -> None:
        try:
            self.load_table_view()
        except Exception as exc:
            logger.exception("TransactionsView.refresh_table: failed - %s", exc)


def show_transactions_view(main_window) -> None:
    """Ensure a TransactionsView exists in the application's central stack
    and make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    tv = getattr(main_window, "_transactions_view", None)
    if tv is None:
        tv = TransactionsView(main_window)
        setattr(main_window, "_transactions_view", tv)
        main_window._stack.addWidget(tv)

    main_window._stack.setCurrentWidget(tv)
