"""Helper for creating the main window menu bar.

This module provides a `MainMenuBar` class that encapsulates the logic for
creating the application's standard menus. A small wrapper function
`create_menu_bar` is provided for backward compatibility with call sites that
expect the former functional API.

The class accepts optional callbacks for actions that depend on external
widgets (for example, showing dialogs or toggling fullscreen) and uses the
provided `parent` as the QAction parent so ownership and memory management
remain consistent with Qt's expectations.
"""
from __future__ import annotations


from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction


class MainMenuBar(QMenuBar):
    """Standard application menu bar as a QMenuBar subclass.

    Instantiate with the main window as the parent: MainMenuBar(main_window)
    The bar will attach itself to the main window during initialization.
    """

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.setObjectName("mainMenuBar")
        self._setup_menus()
        # Attach to the main window so QMainWindow knows about this menu bar
        try:
            self.main_window.setMenuBar(self)
        except Exception:
            # If the main window can't accept a menu bar, ignore silently
            pass

    def toggle_fullscreen(self, *_args) -> None:
        if self.main_window.isFullScreen():
            self.main_window.showNormal()
        else:
            self.main_window.showFullScreen()

    def show_about(self, *_args) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self.main_window,
            "About Club Social Paraiso App",
            "Sistema de gestión del Club Social Paraiso\n\nVersión 1.0\n\nDesarrollado por\nSergio Alfonso Gutierrez.",
        )

    def not_implemented(self, name: str, *_args) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self.main_window, name, f"'{name}' is not implemented yet."
        )

    def _setup_menus(self) -> None:
        """Create and add all menus and actions to this menu bar."""
        self.clear()

        # --- File menu ---
        file_menu = self.addMenu("&File")

        act_new = QAction("&New", self)
        act_new.setShortcut("Ctrl+N")
        act_new.setStatusTip("Create a new item")
        act_new.triggered.connect(lambda *_args, name="New": self.not_implemented(name))
        file_menu.addAction(act_new)

        act_open = QAction("&Open...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.setStatusTip("Open an existing file")
        act_open.triggered.connect(lambda *_args, name="Open": self.not_implemented(name))
        file_menu.addAction(act_open)

        act_save = QAction("&Save", self)
        act_save.setShortcut("Ctrl+S")
        act_save.setStatusTip("Save the current file")
        act_save.triggered.connect(lambda *_args, name="Save": self.not_implemented(name))
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.setStatusTip("Exit the application")
        act_exit.triggered.connect(self.main_window.close)
        file_menu.addAction(act_exit)

        # --- Edit menu ---
        edit_menu = self.addMenu("&Edit")

        act_undo = QAction("&Undo", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(lambda *_args, name="Undo": self.not_implemented(name))
        edit_menu.addAction(act_undo)

        act_redo = QAction("&Redo", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(lambda *_args, name="Redo": self.not_implemented(name))
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_cut = QAction("Cu&t", self)
        act_cut.setShortcut("Ctrl+X")
        act_cut.triggered.connect(lambda *_args, name="Cut": self.not_implemented(name))
        edit_menu.addAction(act_cut)

        act_copy = QAction("&Copy", self)
        act_copy.setShortcut("Ctrl+C")
        act_copy.triggered.connect(lambda *_args, name="Copy": self.not_implemented(name))
        edit_menu.addAction(act_copy)

        act_paste = QAction("&Paste", self)
        act_paste.setShortcut("Ctrl+V")
        act_paste.triggered.connect(lambda *_args, name="Paste": self.not_implemented(name))
        edit_menu.addAction(act_paste)

        # --- View menu ---
        view_menu = self.addMenu("&View")
        act_toggle_fullscreen = QAction("Toggle &Fullscreen", self)
        act_toggle_fullscreen.setShortcut("F11")
        act_toggle_fullscreen.setStatusTip("Toggle full screen mode")
        act_toggle_fullscreen.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(act_toggle_fullscreen)

        # --- Help menu ---
        help_menu = self.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.setStatusTip("About this application")
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)
