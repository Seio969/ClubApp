"""Members menu view.

Layout requested:
- Top: a horizontal "roll" that will hold buttons for future table/views.
- Below the top bar, left: the query results (table view).
- Below the top bar, right: a vertical menu with buttons: Buscar (uses the top bar search input), Filtros, Anadir miembro.

This file provides a ready-to-use QWidget that can be added to the main window stack.
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
    QMenu,
    QSizePolicy,
    QTableView,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt


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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top rolling views bar -------------------------------------------------
        top_bar = QWidget(self)
        top_bar.setObjectName("topBar")
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 6, 6, 6)
        # Reduce global spacing so we control the exact gap after the back button.
        top_layout.setSpacing(0)

        # Back button to return to main menu
        back_button = QPushButton("← Volver")
        back_button.setObjectName("backButton")
        back_button.setToolTip("Volver al menú principal")
        back_button.setMaximumWidth(100)
        back_button.clicked.connect(self.on_back_to_main_menu)
        top_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)

        # Small fixed gap of 8 pixels so the search input sits right next to the back button
        top_layout.addSpacing(8)

        # A small search input on the top bar (the right-side Buscar button will use this)
        self.search_input = QLineEdit(top_bar)
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(28)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_input.returnPressed.connect(self.on_search)
        top_layout.addWidget(self.search_input, Qt.AlignmentFlag.AlignLeft)

        # Buscar button - uses the top bar input as requested
        btn_search = QPushButton("Buscar")
        btn_search.setToolTip("Buscar usando el texto del campo superior")
        btn_search.setMaximumWidth(100)
        btn_search.clicked.connect(self.on_search)
        top_layout.addWidget(btn_search)

        # Push the views dropdown to the far right so the left-side controls remain packed.
        top_layout.addStretch(1)

        self.views_button = QToolButton(top_bar)
        self.views_button.setObjectName("viewsButton")
        self.views_button.setText("Vistas")
        self.views_button.setToolTip("Seleccionar vista")
        # Show the menu instantly when the button is clicked on the arrow
        self.views_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # Set longer minimum width to accommodate text + arrow
        self.views_button.setMinimumWidth(180)
        # Set text on the left, arrow on the right
        self.views_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.views_menu = QMenu(self.views_button)
        self.views_button.setMenu(self.views_menu)
        # Make the button take available horizontal space but keep a fixed height
        self.views_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_layout.addWidget(self.views_button, 0, Qt.AlignmentFlag.AlignLeft)



        main_layout.addWidget(top_bar)

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
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        central_layout.addWidget(self.table, 3)
        # Ensure the layout uses the desired 3:1 horizontal stretch
        central_layout.setStretch(0, 3)

        # Right: vertical menu with buttons
        right_menu = QWidget(central)
        right_menu.setObjectName("rightMenu")
        # Allow the right menu to expand vertically to match the table height
        right_menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_menu)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        # Keep controls aligned to the top; stretch will push the add button down
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)


        # Filtros button
        btn_filters = QPushButton("Filtros")
        btn_filters.clicked.connect(self.on_filters)
        right_layout.addWidget(btn_filters)

        # Spacer to push add button to bottom-ish
        right_layout.addStretch(1)

        # Anadir miembro button
        btn_add = QPushButton("Añadir miembro")
        btn_add.clicked.connect(self.on_add_member)
        right_layout.addWidget(btn_add)

        central_layout.addWidget(right_menu, 1)
        central_layout.setStretch(1, 1)

        main_layout.addWidget(central)

        # Small, pleasant stylesheet to make layout readable
        self.setStyleSheet(r"""
        #membersMenu { background: #fafafa; }
        #topBar { background: transparent; }
        #viewsLabel { font-weight: 600; margin-right: 6px; }
        QPushButton { min-width: 90px; min-height: 28px; }
        #backButton { 
            background-color: #f0f0f0; 
            border: 1px solid #ccc; 
            border-radius: 4px; 
            font-weight: bold;
            color: #333;
        }
        #backButton:hover { 
            background-color: #e0e0e0; 
            border-color: #999; 
        }
        #backButton:pressed { 
            background-color: #d0d0d0; 
        }
        #resultsTable { background: #ffffff; }
        """)

        # For quick visual testing: populate the views dropdown menu with demo
        # entries so you can press the arrow and see it expand downward.
        # This can be removed in production.
        self._populate_demo_views()

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

    def on_search(self) -> None:
        """Perform a simple search using the text in the top bar input.

        This is intentionally minimal: it clears the table and inserts a single
        row containing the search text to show data flow.
        """
        text = self.search_input.text().strip()
        print(f"Buscar: '{text}'")
        # Replace model contents with a sample row for demonstration
        self.model.removeRows(0, self.model.rowCount())
        if text:
            row = [QStandardItem("1"), QStandardItem(text), QStandardItem("n/a@example.com"), QStandardItem("Activo")]
            self.model.appendRow(row)

    def on_filters(self) -> None:
        # Placeholder for filter dialog/controls
        print("Abrir filtros (placeholder)")

    def on_add_member(self) -> None:
        # Placeholder: real implementation should open the member form
        print("Añadir miembro (placeholder)")


    def _populate_demo_views(self, count: int = 12) -> None:
        """Add demo actions to the views dropdown menu to demonstrate the
        downward-expanding menu behaviour.

        Each action will call `on_select_view` with the view name.
        """
        self.views_menu.clear()
        for i in range(count):
            name = f"Vista {i+1}"
            action = self.views_menu.addAction(name)
            # Connect using a lambda that captures the current name
            action.triggered.connect(lambda checked=False, n=name: self.on_select_view(n))



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

