"""Simple home/main menu widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QSpacerItem,
    QMenuBar,
    QMenu,
    QMessageBox,
    QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction
from ui.views.members.members_menu_view import show_members_view



class MainMenuWidget(QWidget):
	"""A tiny main menu used as the application's home page.

	Keep this deliberately simple: a welcome message and a placeholder
	button to add more features later.
	"""

	def __init__(self, main_window):
		super().__init__()
		self.main_window = main_window  # Reference to the main window if needed
		# Will lazily create and store sub-views (so they can be added to the
		# application's central QStackedWidget). Example: members view below.
		self._members_view = None

		# Widget identity (used by the stylesheet)
		self.setObjectName("mainMenu")

		# Create the standard menu bar on the main window
		self._create_menu_bar()

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		layout.addItem(QSpacerItem(0, 100, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))  # Space between top and title
		# Title
		title = QLabel("Sistema de gestión del Club Social Paraiso")
		# Set title properties
		title.setObjectName("title")
		title.setAlignment(Qt.AlignmentFlag.AlignTop) 	# Align top vertically
		title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) 		# Fixed size
		title.setStyleSheet("font-size: 35px; font-weight: 700;") 		# Large, bold font
		# Add a subtle glow to make the title stand out on a dark/black background
		shadow = QGraphicsDropShadowEffect(self)
		shadow.setBlurRadius(18)
		shadow.setOffset(0, 3)
		# Use a very faint light color so the title pops slightly from pure black
		shadow.setColor(QColor(255, 255, 255, 30))
		title.setGraphicsEffect(shadow)
		layout.addWidget(title) 		# Add title to layout
		layout.addItem(QSpacerItem(0, 50, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))  # Space between title and buttons

        # Main menu buttons
		# List of main menu buttons
		buttons_main_menu = [
			"🧑‍🤝‍🧑 Gestionar Miembros",
			"💸 Transacciones",
			"📊 Reportes",
			"⚙️ Ajustes",
			"pene",
			"pito"
		]

		# Create and add buttons to the layout
		for button in buttons_main_menu:
			# Create buttons for main menu options
			btn = QPushButton(button)
			# Set button properties
			btn.setEnabled(True)  # Placeholder: enable when implemented
			btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
			btn.setStyleSheet("font-size: 20px;")
			# Change cursor on hover
			btn.setCursor(Qt.CursorShape.PointingHandCursor)
			# Set fixed size for buttons
			btn.setMinimumWidth(400)
			btn.setMinimumHeight(40)
			# Add button to layout and center it
			layout.addWidget(btn)
			layout.setAlignment(btn, Qt.AlignmentFlag.AlignCenter)
			layout.addItem(QSpacerItem(0, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

			# Placeholder actions for buttons
			if button.startswith("🧑‍🤝‍🧑"):
				# Use the centralized helper to show/add the members view
				btn.clicked.connect(lambda _checked=False, mw=self.main_window: show_members_view(mw))
			if button.startswith("💸"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))
			if button.startswith("📊"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))
			if button.startswith("⚙️"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))

		layout.addItem(QSpacerItem(0, 220, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))  # Space between buttons and subtitle

		# Subtitle
		subtitle = QStatusBar(self)
		subtitle.showMessage("Versión 1.0")
		# subtitle.setObjectName("subtitle")
		# # Set subtitle properties
		# subtitle.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)        # Align bottom vertically
		# # Keep subtitle from expanding and pushing the title/button area;
		# # use a fixed size (small minimum height) so it stays visually anchored.
		# subtitle.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
		# subtitle.setMinimumHeight(20)
		# layout.addWidget(subtitle)        # Add subtitle to layout


		# Apply an overall stylesheet for colors and nicer buttons
		self.setStyleSheet(r"""
/* Solid black background for the main menu */
#mainMenu {
    background-color: #000000;
}

/* Title and subtitle styling */
#title {
    color: #ffffff;
    letter-spacing: 1px;
	font-family: "SF Pro Display", sans-serif;
}
#subtitle {
    color: #cfe8e6;
    font-size: 14px;
}

/* Buttons: modern rounded gradient with hover/pressed states */
QPushButton {
    color: #000000;
    /* Darker green gradient */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #245c1a, stop:1 #388e3c);
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
}
QPushButton:hover {
    /* Slightly brighter dark green on hover */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2e7031, stop:1 #43a047);
}
QPushButton:pressed {
    /* Even darker green when pressed */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b3c13, stop:1 #2e7031);
}
QPushButton:disabled {
    background: #666b75;
    color: #cfcfcf;
}
""")


	# Show the home (main menu) page
	def show_home(self) -> None:
		"""Switch to the home (main menu) page."""
		self.main_window._stack.setCurrentWidget(self.main_window._home)

	# New helper methods for the menu actions
	def _create_menu_bar(self) -> None:
		"""Add a standard menu bar (File, Edit, View, Help) to the main window."""
		# Ensure there is a menu bar on the main window and start fresh
		menubar: QMenuBar = self.main_window.menuBar()
		menubar.clear()

		# --- File menu ---
		file_menu = menubar.addMenu("&File")

		act_new = QAction("&New", self)
		act_new.setShortcut("Ctrl+N")
		act_new.setStatusTip("Create a new item")
		act_new.triggered.connect(lambda: self._not_implemented("New"))
		file_menu.addAction(act_new)

		act_open = QAction("&Open...", self)
		act_open.setShortcut("Ctrl+O")
		act_open.setStatusTip("Open an existing file")
		act_open.triggered.connect(lambda: self._not_implemented("Open"))
		file_menu.addAction(act_open)

		act_save = QAction("&Save", self)
		act_save.setShortcut("Ctrl+S")
		act_save.setStatusTip("Save the current file")
		act_save.triggered.connect(lambda: self._not_implemented("Save"))
		file_menu.addAction(act_save)

		file_menu.addSeparator()

		act_exit = QAction("E&xit", self)
		act_exit.setShortcut("Ctrl+Q")
		act_exit.setStatusTip("Exit the application")
		act_exit.triggered.connect(self.main_window.close)
		file_menu.addAction(act_exit)

		# --- Edit menu ---
		edit_menu = menubar.addMenu("&Edit")

		act_undo = QAction("&Undo", self)
		act_undo.setShortcut("Ctrl+Z")
		act_undo.triggered.connect(lambda: self._not_implemented("Undo"))
		edit_menu.addAction(act_undo)

		act_redo = QAction("&Redo", self)
		act_redo.setShortcut("Ctrl+Y")
		act_redo.triggered.connect(lambda: self._not_implemented("Redo"))
		edit_menu.addAction(act_redo)

		edit_menu.addSeparator()

		act_cut = QAction("Cu&t", self)
		act_cut.setShortcut("Ctrl+X")
		act_cut.triggered.connect(lambda: self._not_implemented("Cut"))
		edit_menu.addAction(act_cut)

		act_copy = QAction("&Copy", self)
		act_copy.setShortcut("Ctrl+C")
		act_copy.triggered.connect(lambda: self._not_implemented("Copy"))
		edit_menu.addAction(act_copy)

		act_paste = QAction("&Paste", self)
		act_paste.setShortcut("Ctrl+V")
		act_paste.triggered.connect(lambda: self._not_implemented("Paste"))
		edit_menu.addAction(act_paste)

		# --- View menu ---
		view_menu = menubar.addMenu("&View")
		act_toggle_fullscreen = QAction("Toggle &Fullscreen", self)
		act_toggle_fullscreen.setShortcut("F11")
		act_toggle_fullscreen.setStatusTip("Toggle full screen mode")
		act_toggle_fullscreen.triggered.connect(self._toggle_fullscreen)
		view_menu.addAction(act_toggle_fullscreen)

		# --- Help menu ---
		help_menu = menubar.addMenu("&Help")
		act_about = QAction("&About", self)
		act_about.setStatusTip("About this application")
		act_about.triggered.connect(self._show_about)
		help_menu.addAction(act_about)

	def _toggle_fullscreen(self) -> None:
		"""Toggle the main window fullscreen state."""
		if self.main_window.isFullScreen():
			self.main_window.showNormal()
		else:
			self.main_window.showFullScreen()

	def _show_about(self) -> None:
		"""Show a simple About dialog."""
		QMessageBox.about(
			self.main_window,
			"About Club Social Paraiso",
			"Sistema de gestión del Club Social Paraiso\n\nVersión 1.0",
		)

	def _not_implemented(self, name: str) -> None:
		"""Generic stub for unimplemented menu actions."""
		# Keep this minimal: show an informational message in a dialog
		QMessageBox.information(self.main_window, name, f"'{name}' is not implemented yet.")


