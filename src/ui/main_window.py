"""Main application window using PySide6.

This module provides a small, well-documented MainWindow and a
`run_main_window` entrypoint. It intentionally does not run any GUI code
at import time so it is safe to import for tests and static checks.

The design is minimal on purpose so you can expand it step-by-step.
"""

from __future__ import annotations

from typing import Optional
import sys

from PySide6.QtWidgets import (
	QApplication,
	QMainWindow,
	QStackedWidget,
)

from ui.views.main_menu_widget import MainMenuWidget


class MainWindow(QMainWindow):
	"""Main application window.

	- Contains a QStackedWidget as the central widget.
	- Provides a small API to show the home (main menu) widget.

	This is deliberately small so we can grow the UI in tiny steps.
	"""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("AppClub")
		self.resize(900, 600)  # Big enough for a comfortable start

		# Central stack to host different pages (home, forms, reports, ...)
		self._stack = QStackedWidget()
		self.setCentralWidget(self._stack)

		# Create and register the home menu widget
		self._home = MainMenuWidget(self)
		self._stack.addWidget(self._home)


def run_main_window(argv: Optional[list[str]] = None) -> int:
	"""Create QApplication, show MainWindow and run the event loop.

	Call this from a safe entrypoint (for example `src/main.py`).

	Returns the application's exit code.
	"""

	if argv is None:
		argv = sys.argv

	app = QApplication(list(sys.argv))
	w = MainWindow()
	w.show()
	return app.exec()


