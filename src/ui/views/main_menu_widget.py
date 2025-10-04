"""Simple home/main menu widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
	QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction
from ui.views.members.members_menu_view import show_members_view
from ui.views.menu_bar import create_menu_bar



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

		# Menus are created centrally by MainWindow; the widget should not
		# create the application's menu bar itself.

		layout = QVBoxLayout(self)
		# Keep the main layout aligned to the top so the top area (title)
		# is independent from the button-area which receives the expanding
		# vertical stretch below.
		layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		# Fixed space between top and title so the title remains visually fixed
		layout.addSpacing(100)
		# Title
		title = QLabel("Sistema de gestión del Club Social Paraiso")
		# Set title properties
		title.setObjectName("title")
		# Align the label text to the top and horizontally center the widget
		# within the parent layout. Allow the label to expand horizontally so
		# centering works even when the button-area changes size.
		title.setAlignment(Qt.AlignmentFlag.AlignTop) 	# Align top vertically (text)
		title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		title.setStyleSheet("font-size: 35px; font-weight: 700;") 		# Large, bold font
		# Add a subtle glow to make the title stand out on a dark/black background
		shadow = QGraphicsDropShadowEffect(self)
		shadow.setBlurRadius(18)
		shadow.setOffset(0, 3)
		# Use a very faint light color so the title pops slightly from pure black
		shadow.setColor(QColor(255, 255, 255, 30))
		title.setGraphicsEffect(shadow)
		# Add the title widget centered horizontally and aligned to the top
		layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
		# Fixed small gap between title and buttons; the buttons layout will
		# receive all available extra vertical space (see addLayout(..., 1)).
		layout.addSpacing(50)

		layoutButtons = QGridLayout()
		# Give the buttons layout the expanding stretch so when the window
		# grows vertically the button-area gets the extra space.
		# Use a grid layout for better control of button placement.
		# We'll put buttons in a centered grid (2 columns by default).
		layout.addLayout(layoutButtons, 1)
        # Main menu buttons
		# List of main menu buttons
		buttons_main_menu = [
			"🧑‍🤝‍🧑 Gestionar Miembros",
			"⚙️ Ajustes"
		]

		# Create and add buttons to the grid layout
		columns = 2
		row = 0
		col = 0
		for idx, button in enumerate(buttons_main_menu):
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
			# Add button to grid and center it in the cell
			layoutButtons.addWidget(btn, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

			# Advance grid coordinates
			col += 1
			if col >= columns:
				col = 0
				row += 1

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

		# Keep a fixed gap below the buttons area so the title/button
		# grouping remains visually balanced.
		layout.addSpacing(220)



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


	# Menu-related callbacks have been centralized in MainWindow. The widget
	# no longer needs to implement _toggle_fullscreen, _show_about or
	# _not_implemented; the MainWindow provides those and passes them to the
	# shared create_menu_bar helper during initialization.


