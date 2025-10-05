
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
from ui.styles import MAIN_MENU_STYLESHEET, TITLE_STYLE, BUTTON_FONT_STYLE


class MainMenuWidget(QWidget):
	"""Main menu used as the application's home page."""

	def __init__(self, main_window):
		super().__init__()
		self.main_window = main_window
		self._members_view = None

		self.setObjectName("mainMenu")

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		layout.addSpacing(100)
		title = QLabel("Sistema de gestión del Club Social Paraiso")
		title.setObjectName("title")
		title.setAlignment(Qt.AlignmentFlag.AlignTop)
		title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		title.setStyleSheet(TITLE_STYLE)
		shadow = QGraphicsDropShadowEffect(self)
		shadow.setBlurRadius(18)
		shadow.setOffset(0, 3)
		shadow.setColor(QColor(255, 255, 255, 30))
		title.setGraphicsEffect(shadow)
		layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
		layout.addSpacing(50)

		layoutButtons = QGridLayout()
		layout.addLayout(layoutButtons, 1)

		buttons_main_menu = [
			"🧑‍🤝‍🧑 Gestionar Miembros",
			"⚙️ Ajustes",
		]

		columns = 2
		row = 0
		col = 0
		for idx, button in enumerate(buttons_main_menu):
			btn = QPushButton(button)
			btn.setEnabled(True)
			btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
			btn.setStyleSheet(BUTTON_FONT_STYLE)
			btn.setCursor(Qt.CursorShape.PointingHandCursor)
			btn.setMinimumWidth(400)
			btn.setMinimumHeight(40)
			layoutButtons.addWidget(btn, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

			col += 1
			if col >= columns:
				col = 0
				row += 1

			if button.startswith("🧑‍🤝‍🧑"):
				btn.clicked.connect(lambda _checked=False, mw=self.main_window: show_members_view(mw))
			if button.startswith("💸"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))
			if button.startswith("📊"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))
			if button.startswith("⚙️"):
				btn.clicked.connect(lambda checked, b=button: print(f"{b} button clicked"))

		layout.addSpacing(220)

		self.setStyleSheet(MAIN_MENU_STYLESHEET)

	def show_home(self) -> None:
		"""Switch to the home (main menu) page."""
		self.main_window._stack.setCurrentWidget(self.main_window._home)



