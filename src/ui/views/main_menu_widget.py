
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
from features.members.menu_view import show_members_view
from features.settings.menu_view import show_settings_view
from features.transactions.view import show_transactions_view
from ui.styles import MAIN_MENU_STYLESHEET, TITLE_STYLE, BUTTON_FONT_STYLE
from utils.logger import get_logger
logger = get_logger(__name__)


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

		# Each entry is (route_id, label, handler) - route_id feeds the
		# button's objectName (useful for tests/future styling) and handler
		# is connected directly, rather than dispatching on an emoji prefix
		# parsed out of the label (the old approach - brittle already, and
		# wouldn't scale to more buttons; flagged in UI_PROPOSAL.md finding
		# #5 and fixed here rather than extended further).
		buttons_main_menu = [
			("miembros", "🧑‍🤝‍🧑 Gestionar Miembros", show_members_view),
			("transacciones", "🧾 Transacciones", show_transactions_view),
			("ajustes", "⚙️ Ajustes", show_settings_view),
		]

		columns = 2
		row = 0
		col = 0
		for route_id, label, handler in buttons_main_menu:
			btn = QPushButton(label)
			btn.setObjectName(f"menuButton_{route_id}")
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

			btn.clicked.connect(lambda _checked=False, mw=self.main_window, h=handler: h(mw))

		layout.addSpacing(220)

		self.setStyleSheet(MAIN_MENU_STYLESHEET)

	def show_home(self) -> None:
		"""Switch to the home (main menu) page."""
		self.main_window._stack.setCurrentWidget(self.main_window._home)



