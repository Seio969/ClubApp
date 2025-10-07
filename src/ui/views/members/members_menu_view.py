"""Members menu view.

Layout requested:
- Top: a horizontal "roll" that will hold buttons for future table/views.
- Below the top bar: the query results (table view) occupying the main area.

This file provides a ready-to-use QWidget that can be added to the main window stack.
The right-side vertical action menu was removed per UI simplification.
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
    QScrollArea,
    QToolButton,
    QStyle,
    QMenu,
    QSizePolicy,
    QTableView,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction, QIntValidator
from PySide6.QtCore import Qt, QSize
import unicodedata

from .members_toolbar import MembersToolBar
from ui.styles import MEMBERS_MENU_STYLESHEET
from services.members_menu_service import MembersMenuService


class MembersMenuView(QWidget):
    """Members menu view widget.

    Contract (tiny):
    - Inputs: none (UI-only). Search text is taken from the top bar input.
    - Outputs: signals currently implemented as simple method hooks/prints.
    - Error modes: none (placeholder).

    The widget intentionally keeps behaviour minimal; hooks are provided where
    real service calls can be attached later.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("membersMenu")
        self.main_window = parent  # Store reference to main window for navigation
        self._current_view_name = None  # Track currently loaded view for refreshing

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top rolling views bar -------------------------------------------------
        top_bar = QWidget(self)
        top_bar.setObjectName("topBar")
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 6, 6, 6)
        # Reduce global spacing so we control the exact gaps inside groups.
        top_layout.setSpacing(0)

        # Left group: back button (compact)
        left_group = QWidget(top_bar)
        left_group.setObjectName("topLeftGroup")
        left_layout = QHBoxLayout(left_group)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        back_button = QPushButton()
        back_button.setObjectName("backButton")
        back_button.setToolTip("Volver al menú principal")
        back_button.setMaximumWidth(120)
        back_button.setText("Volver")
        back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        back_button.clicked.connect(self.on_back_to_main_menu)
        left_layout.addWidget(back_button)

        top_layout.addWidget(left_group, 0, Qt.AlignmentFlag.AlignLeft)

        # Center group: nicer, slightly larger search area
        center_group = QWidget(top_bar)
        center_group.setObjectName("topCenterGroup")
        center_layout = QHBoxLayout(center_group)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        self.search_input = QLineEdit(center_group)
        self.search_input.setPlaceholderText("Buscar miembros, email, id...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(34)
        self.search_input.setMinimumWidth(300)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.search_input.returnPressed.connect(self.on_search)
        center_layout.addWidget(self.search_input)

        btn_search = QPushButton("Buscar")
        btn_search.setToolTip("Buscar usando el texto del campo superior")
        btn_search.setMaximumWidth(110)
        btn_search.setMinimumHeight(34)
        btn_search.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        btn_search.clicked.connect(self.on_search)
        center_layout.addWidget(btn_search)

        # Use stretches to keep the search area visually centered between left and right groups
        top_layout.addStretch(1)
        top_layout.addWidget(center_group, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Middle group: limit entry
        middle_group = QWidget(top_bar)
        middle_group.setObjectName("topMiddleGroup")
        middle_layout = QHBoxLayout(middle_group)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(6)

        limit_label = QLabel("Límite:")
        limit_label.setToolTip("Número máximo de resultados a mostrar")
        middle_layout.addWidget(limit_label)

        self.limit_input = QLineEdit(middle_group)
        self.limit_input.setPlaceholderText("")
        self.limit_input.setText("0")  # Default value
        self.limit_input.setToolTip("Número máximo de resultados a mostrar (por defecto 100)")
        self.limit_input.setMaximumWidth(80)
        self.limit_input.setMinimumHeight(34)
        self.limit_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Only allow numbers (0 means "no limit")
        self.limit_input.setValidator(QIntValidator(0, 99999, self))
        # Refresh view when Enter is pressed
        self.limit_input.returnPressed.connect(self.on_limit_changed)
        middle_layout.addWidget(self.limit_input)

        top_layout.addWidget(middle_group, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        # Right group: views menu and (future) actions
        right_group = QWidget(top_bar)
        right_group.setObjectName("topRightGroup")
        right_layout = QHBoxLayout(right_group)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.views_button = QToolButton(right_group)
        self.views_button.setObjectName("viewsButton")
        self.views_button.setText("Vistas")
        self.views_button.setToolTip("Seleccionar vista")
        self.views_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.views_button.setMinimumWidth(140)
        self.views_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.views_menu = QMenu(self.views_button)
        self.views_button.setMenu(self.views_menu)
        self.views_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.views_button.setAutoRaise(True)
        right_layout.addWidget(self.views_button)

        # Filters dropdown: will contain checkable actions for each column
        self.filters_button = QToolButton(right_group)
        self.filters_button.setObjectName("filtersButton")
        self.filters_button.setText("Filtros")
        self.filters_button.setToolTip("Mostrar/ocultar columnas")
        self.filters_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.filters_button.setMinimumWidth(140)
        self.filters_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.filters_menu = QMenu(self.filters_button)
        self.filters_button.setMenu(self.filters_menu)
        self.filters_button.setIcon(self.style().standardIcon(QStyle.SP_DialogYesButton))
        self.filters_button.setAutoRaise(True)
        right_layout.addWidget(self.filters_button)

        top_layout.addWidget(right_group, 0, Qt.AlignmentFlag.AlignRight)



        main_layout.addWidget(top_bar)

        # --- Toolbar just below the top bar ----------------------------------
        # Use the specialized MembersToolBar for member-specific actions
        self.toolbar = MembersToolBar(self)
        main_layout.addWidget(self.toolbar)

        # --- Central area: left -> results table, right -> action menu -------------
        central = QWidget(self)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(12)

        # Left: results table
        self.table = QTableView(central)
        self.table.setObjectName("resultsTable")
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        # Minimal model. Real app should replace with a proper model connected to DB.
        self.model = QStandardItemModel(0, 4, self)
        self.model.setHorizontalHeaderLabels(["ID", "Nombre", "Email", "Estado"])
        self.table.setModel(self.model)
        header = self.table.horizontalHeader()
        # Allow the user to resize columns interactively instead of forcing
        # all columns to stretch. Provide a sensible default section size and
        # allow moving sections if desired.
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(False)
        header.setSectionsMovable(True)

        # Allow clicking headers to trigger sorting behavior
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self._on_header_clicked)

        # Track sorting state: None means no sorting active
        self._sort_column = None
        self._sort_order = None
        # Remember last search text so we can restore search results when clearing sort
        self._last_search_text = None
        
        # Set table and model references for the toolbar
        self.toolbar.set_table_references(self.table, self.model)
        # Backend/service used by the view
        self._service = MembersMenuService()
        # Populate filters menu based on current model columns
        self._populate_filters_menu()
        
        central_layout.addWidget(self.table, 3)
        # Ensure the layout uses the desired 3:1 horizontal stretch
        central_layout.setStretch(0, 3)

        # (Right-side action menu removed.) The table occupies the central area.
        # Ensure the table stretches to take available horizontal space.
        main_layout.addWidget(central)

        # Small, pleasant stylesheet to make layout readable
        self.setStyleSheet(MEMBERS_MENU_STYLESHEET)
        # Populate views dropdown dynamically from service-registered views
        self._populate_db_views()

        # Try to load a preferred view automatically (if available).
        # Prefer 'socios' (case-insensitive). Fallback to the first registered view.
        try:
            views = self._service.get_views()
            chosen = None
            if views:
                for v in views:
                    try:
                        #TODO Add this variable to settings or config to be chosen by the user
                        if str(v).lower() == "socios":
                            chosen = v
                            break
                    except Exception:
                        continue
                if chosen is None:
                    chosen = views[0]
                if chosen:
                    self.load_table_view(chosen)
        except Exception:
            pass

    # Track the currently loaded view name so the toolbar can request a
    # refresh that reloads the same data from the DB.
    # (already initialized at top of __init__)
    #TODO have a look at above comment
        

    # ---------------------- placeholder event handlers -------------------------
    def on_back_to_main_menu(self) -> None:
        """Navigate back to the main menu."""
        if self.main_window and hasattr(self.main_window, '_stack') and hasattr(self.main_window, '_home'):
            self.main_window._stack.setCurrentWidget(self.main_window._home)
        else:
            print("No se pudo navegar al menú principal")

    def on_select_view(self, name: str) -> None:
        """Called when the user clicks one of the view buttons in the top rolling bar.

        In a real app this would switch the visible table/model to the selected view.
        """
        print(f"Seleccionada vista: {name}")
        # In a real app switching views would change the model/columns.
        # For now, repopulate the filters menu so it reflects the active model.
        self._populate_filters_menu()

    def _populate_filters_menu(self) -> None:
        """Create checkable actions for each column in the current model.

        By default all columns are visible (checked). Toggling an action
        will hide/show the corresponding column in the table view.
        """
        # Ensure menu exists
        if not hasattr(self, "filters_menu") or self.filters_menu is None:
            self.filters_menu = QMenu(self)
            self.filters_button.setMenu(self.filters_menu)

        self.filters_menu.clear()

        # Use the service to extract header labels and build actions
        labels = self._service.get_filter_labels(self.model)
        for col, label in enumerate(labels):
            action = QAction(label, self.filters_menu)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(col))
            action.setData(col)
            action.toggled.connect(lambda checked, idx=col: self.table.setColumnHidden(idx, not checked))
            self.filters_menu.addAction(action)

    def get_limit(self) -> Optional[int]:
        """Get the limit value from the limit input field.

        Returns:
            Optional[int]: The limit value. If the user enters 0 or leaves
            the field empty/invalid, returns None which means "no limit".
        """
        try:
            text = self.limit_input.text().strip()
            if not text:
                return None  # Empty means no limit
            limit = int(text)
            # 0 is treated as "no limit" per UI convention
            if limit == 0:
                return None
            # Ensure within valid positive range
            return max(1, min(limit, 99999))
        except (ValueError, AttributeError):
            return None  # Treat parse errors as "no limit"

    def on_search(self) -> None:
        """Perform a simple search using the text in the top bar input.

        This is intentionally minimal: it clears the table and inserts a single
        row containing the search text to show data flow.
        """
        text = self.search_input.text().strip()
        limit = self.get_limit()
        # remember last search so clearing sort can re-run it
        self._last_search_text = text
        print(f"Buscar: '{text}' con límite: {limit}")
        # Delegate search/population to service
        added = self._service.search_members(text, self.model, limit=limit)
        print(f"Search added {added} rows")

    def on_limit_changed(self) -> None:
        """Handle when user presses Enter in the limit input field.
        
        This will refresh the current view with the new limit.
        """
        limit = self.get_limit()
        print(f"Límite cambiado a: {limit if limit is not None else 'sin límite'}")
        
        # If we have a current view loaded, refresh it with the new limit
        if hasattr(self, '_current_view_name') and self._current_view_name:
            print(f"Refrescando vista '{self._current_view_name}' con nuevo límite")
            try:
                self.load_table_view(self._current_view_name)
            except Exception as exc:
                print(f"Error al refrescar vista con nuevo límite: {exc}")
        else:
            # If no specific view is loaded, try to refresh the table
            print("Refrescando tabla con nuevo límite")
            try:
                self.refresh_table()
            except Exception as exc:
                print(f"Error al refrescar tabla con nuevo límite: {exc}")


    def _populate_db_views(self) -> None:
        """Populate the views dropdown with actual database table names."""
        self.views_menu.clear()
        try:
            views = self._service.get_views()
            if not views:
                # fallback: keep a demo entry so the menu isn't empty
                action = self.views_menu.addAction("No hay vistas registradas")
                action.setEnabled(False)
                return

            for name in views:
                action = self.views_menu.addAction(name)
                action.triggered.connect(lambda checked=False, n=name: self.load_table_view(n))
        except Exception as exc:
            print("MembersMenuView._populate_db_views: failed -", exc)

    def load_table_view(self, table_name: str) -> None:
        """Load the named table into the results table by querying the DB.

        This calls the service.fetch_view which validates/dispatches the view
        (table/sql/callable) and populates the model.
        """
        print(f"Cargando vista: {table_name}")
        limit = self.get_limit()
        print(f"Aplicando límite: {limit}")
        # remember which view is currently loaded so refresh can re-run it
        self._current_view_name = table_name
        added = self._service.fetch_view(table_name, self.model, limit=limit)
        print(f"Cargadas {added} filas desde vista '{table_name}' con límite {limit}")
        # Refresh filters menu to match new columns
        self._populate_filters_menu()
        # If a sort is currently active, try to re-apply it on the newly loaded model
        try:
            self._maybe_reapply_sort()
        except Exception:
            # Non-critical; ignore reapply failures
            pass

    def refresh_table(self) -> None:
        """Reload the currently selected/loaded table view.

        This re-invokes the same logic as `load_table_view` for the
        previously loaded view name. If no view is loaded, try to load
        the first available view from the service.
        """
        if self._current_view_name:
            try:
                self.load_table_view(self._current_view_name)
            except Exception as exc:
                print("MembersMenuView.refresh_table: failed -", exc)
            return

        # No current view selected; attempt to load the first registered view
        try:
            views = self._service.get_views()
            if views:
                self.load_table_view(views[0])
        except Exception:
            # nothing to refresh
            pass

    # Handle tildes and accents in sorting and searching by normalizing
    # text values to a diacritic-free form and using that for comparisons.
    # ---------------------- sorting helpers -------------------------

    def _normalize_for_sort(self, value: str) -> str:
        """Return a lowercase, diacritic-free version of the string for sorting.

        This converts characters like 'á' -> 'a', 'ñ' -> 'n', etc., and
        performs a casefold to make comparisons case-insensitive.
        """
        if value is None:
            return ""
        try:
            # Ensure we are working with a string
            s = str(value)
            # Normalize to NFKD and drop combining marks (diacritics)
            nkfd = unicodedata.normalize("NFKD", s)
            stripped = "".join(ch for ch in nkfd if not unicodedata.combining(ch))
            # Use casefold for aggressive case-insensitive compare
            return stripped.casefold().strip()
        except Exception:
            return str(value).casefold() if value is not None else ""

    def _make_sort_key(self, raw: str):
        """Create a sort key that prefers numeric sorting when values look numeric.

        Returns a tuple where the first element is 0 for numeric values and 1
        for text values so numbers sort before text when mixed. The second
        element is the numeric value or the normalized text.
        """
        if raw is None:
            return (1, "")
        s = str(raw).strip()
        # Try integer first, then float
        try:
            ival = int(s)
            return (0, ival)
        except Exception:
            pass
        try:
            fval = float(s)
            return (0, fval)
        except Exception:
            pass
        # Fallback to normalized text
        return (1, self._normalize_for_sort(s))
    def _on_header_clicked(self, index: int) -> None:
        """Handle clicks on header sections to toggle sort state.

        Cycle: (no sort) -> ASC -> DESC -> (no sort)
        Clicking a different column restarts the cycle on that column.
        """
        try:
            # Determine next state
            if self._sort_column is None or self._sort_column != index:
                # New column selected -> start with ascending
                self._sort_column = index
                self._sort_order = Qt.SortOrder.AscendingOrder
                self._apply_sort()
                return

            # Same column clicked again -> toggle
            if self._sort_order == Qt.SortOrder.AscendingOrder:
                self._sort_order = Qt.SortOrder.DescendingOrder
                self._apply_sort()
                return

            if self._sort_order == Qt.SortOrder.DescendingOrder:
                # Third click: clear sorting and restore original order
                self._clear_sort()
                return
        except Exception as exc:
            print("Header click sorting failed:", exc)

    def _apply_sort(self) -> None:
        """Apply the current sort to the model and show indicator."""
        if self._sort_column is None or self._sort_order is None:
            return
        try:
            col = self._sort_column
            ascending = self._sort_order == Qt.SortOrder.AscendingOrder

            # Extract all rows as lists of text values
            rows = []
            row_count = self.model.rowCount()
            col_count = self.model.columnCount()
            for r in range(row_count):
                vals = []
                for c in range(col_count):
                    item = self.model.item(r, c)
                    vals.append("") if item is None else vals.append(item.text())
                rows.append(vals)

            # Stable sort using keys that remove diacritics and prefer numeric ordering
            rows.sort(key=lambda rv: self._make_sort_key(rv[col]), reverse=not ascending)

            # Repopulate model preserving header labels
            from PySide6.QtGui import QStandardItem

            # Capture headers
            try:
                from PySide6.QtCore import Qt as _Qt
                headers = [self.model.headerData(c, _Qt.Orientation.Horizontal) for c in range(col_count)]
            except Exception:
                headers = [self.model.headerData(c, Qt.Orientation.Horizontal) for c in range(col_count)]

            # Clear and rebuild
            self.model.removeRows(0, self.model.rowCount())
            self.model.setColumnCount(col_count)
            if headers:
                self.model.setHorizontalHeaderLabels([str(h) if h is not None else "" for h in headers])

            for vals in rows:
                items = [QStandardItem("" if v is None else str(v)) for v in vals]
                self.model.appendRow(items)

            header = self.table.horizontalHeader()
            header.setSortIndicator(self._sort_column, self._sort_order)
            header.setSortIndicatorShown(True)
        except Exception as exc:
            print("Failed to apply sort:", exc)

    def _clear_sort(self) -> None:
        """Clear any active sort and restore original data order.

        Restoration strategy:
        - If a DB-backed view is loaded, re-run load_table_view to fetch original order.
        - Otherwise, re-run the last search (if any) to restore the previous dataset.
        """
        try:
            self._sort_column = None
            self._sort_order = None
            header = self.table.horizontalHeader()
            header.setSortIndicatorShown(False)

            # Restore data depending on current context
            if getattr(self, "_current_view_name", None):
                # reload current view from service (original order)
                try:
                    self.load_table_view(self._current_view_name)
                    return
                except Exception:
                    pass

            # No current view: if we have a last search text, re-run search
            if self._last_search_text is not None:
                try:
                    # on_search will repopulate model using remembered input
                    # but ensure the input field still contains the same text
                    self.search_input.setText(self._last_search_text)
                    self.on_search()
                    return
                except Exception:
                    pass

            # Fallback: refresh table which may load a default view
            try:
                self.refresh_table()
            except Exception:
                pass
        except Exception as exc:
            print("Failed to clear sort:", exc)

    def _maybe_reapply_sort(self) -> None:
        """Re-apply active sort after the model has been (re)populated.

        This is used after loading a view so user-visible sorting persists
        across reloads when appropriate.
        """
        if self._sort_column is None or self._sort_order is None:
            return
        # Ensure column exists in new model
        try:
            col_count = self.model.columnCount()
            if 0 <= self._sort_column < col_count:
                self._apply_sort()
            else:
                # Invalid for this model: clear sort state and hide indicator
                self._sort_column = None
                self._sort_order = None
                self.table.horizontalHeader().setSortIndicatorShown(False)
        except Exception:
            pass



def show_members_view(main_window) -> None:
    """Ensure a MembersMenuView exists in the application's central stack
    and make it the current widget.

    This helper centralizes the logic of creating/adding the view so
    callers (for example menu buttons) don't need to construct the
    widget themselves.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    # Keep a single instance attached to the main_window to avoid
    # creating many widgets and accidentally calling setCurrentWidget on
    # widgets that are not part of the stack.
    mv = getattr(main_window, "_members_view", None)
    if mv is None:
        mv = MembersMenuView(main_window)  # Pass main_window as parent
        setattr(main_window, "_members_view", mv)
        # Add to the application's central stack
        main_window._stack.addWidget(mv)

    # Make it current
    main_window._stack.setCurrentWidget(mv)

