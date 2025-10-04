"""Helper for creating the main window menu bar.

This module provides a single function `create_menu_bar` that mirrors the
behavior previously implemented as a method on `MainMenuWidget`.

The function is intentionally minimal: it takes callbacks for actions that
depend on the widget instance (not implemented, toggle fullscreen, show about)
and uses the provided `parent` as the QAction parent so ownership and memory
management remain consistent with Qt's expectations.
"""
from __future__ import annotations


from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction


def create_menu_bar(
    main_window,
    parent
) -> None:
    """Add a standard menu bar to the given main window.

    Parameters
    - main_window: the QMainWindow instance whose menuBar() will be used.
    - parent: QObject used as the parent for created QActions (typically the
      widget instance that previously owned the method).
    - not_implemented: callback(name) called for unimplemented actions.
    - toggle_fullscreen: callback() to toggle fullscreen.
    - show_about: callback() to show the about dialog.
    """
    # If callers don't provide callbacks, bind sensible defaults that
    # call the helpers defined later in this module bound to the
    # provided `main_window`. Use lambdas that accept optional args
    # because some Qt signals may pass additional parameters (for
    # example QAction.triggered passes a boolean), and we want the
    # default wrappers to ignore those safely.

    # Ensure there is a menu bar on the main window and start fresh
    menubar: QMenuBar = main_window.menuBar()
    menubar.clear()

    # Helper functions used by menu actions. Define them here so they
    # close over `main_window` and are available when actions are
    # created below. They accept optional args because Qt signals may
    # pass parameters (for example QAction.triggered passes a boolean).
    def toggle_fullscreen(*_args) -> None:
        """Toggle the main window fullscreen state."""
        if main_window.isFullScreen():
            main_window.showNormal()
        else:
            main_window.showFullScreen()


    def show_about(*_args) -> None:
        """Show the application's About dialog for the given main_window."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            main_window,
            "About Club Social Paraiso",
            "Sistema de gestión del Club Social Paraiso\n\nVersión 1.0",
        )


    def not_implemented(name: str, *_args) -> None:
        """Generic stub dialog for unimplemented menu actions.

        Shows a simple informational message attached to the provided
        main_window.
        """
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(main_window, name, f"'{name}' is not implemented yet.")

    # --- File menu ---
    file_menu = menubar.addMenu("&File")

    act_new = QAction("&New", parent)
    act_new.setShortcut("Ctrl+N")
    act_new.setStatusTip("Create a new item")
    act_new.triggered.connect(lambda: not_implemented("New"))
    file_menu.addAction(act_new)

    act_open = QAction("&Open...", parent)
    act_open.setShortcut("Ctrl+O")
    act_open.setStatusTip("Open an existing file")
    act_open.triggered.connect(lambda: not_implemented("Open"))
    file_menu.addAction(act_open)

    act_save = QAction("&Save", parent)
    act_save.setShortcut("Ctrl+S")
    act_save.setStatusTip("Save the current file")
    act_save.triggered.connect(lambda: not_implemented("Save"))
    file_menu.addAction(act_save)

    file_menu.addSeparator()

    act_exit = QAction("E&xit", parent)
    act_exit.setShortcut("Ctrl+Q")
    act_exit.setStatusTip("Exit the application")
    act_exit.triggered.connect(main_window.close)
    file_menu.addAction(act_exit)

    # --- Edit menu ---
    edit_menu = menubar.addMenu("&Edit")

    act_undo = QAction("&Undo", parent)
    act_undo.setShortcut("Ctrl+Z")
    act_undo.triggered.connect(lambda: not_implemented("Undo"))
    edit_menu.addAction(act_undo)

    act_redo = QAction("&Redo", parent)
    act_redo.setShortcut("Ctrl+Y")
    act_redo.triggered.connect(lambda: not_implemented("Redo"))
    edit_menu.addAction(act_redo)

    edit_menu.addSeparator()

    act_cut = QAction("Cu&t", parent)
    act_cut.setShortcut("Ctrl+X")
    act_cut.triggered.connect(lambda: not_implemented("Cut"))
    edit_menu.addAction(act_cut)

    act_copy = QAction("&Copy", parent)
    act_copy.setShortcut("Ctrl+C")
    act_copy.triggered.connect(lambda: not_implemented("Copy"))
    edit_menu.addAction(act_copy)

    act_paste = QAction("&Paste", parent)
    act_paste.setShortcut("Ctrl+V")
    act_paste.triggered.connect(lambda: not_implemented("Paste"))
    edit_menu.addAction(act_paste)

    # --- View menu ---
    view_menu = menubar.addMenu("&View")
    act_toggle_fullscreen = QAction("Toggle &Fullscreen", parent)
    act_toggle_fullscreen.setShortcut("F11")
    act_toggle_fullscreen.setStatusTip("Toggle full screen mode")
    act_toggle_fullscreen.triggered.connect(toggle_fullscreen)
    view_menu.addAction(act_toggle_fullscreen)

    # --- Help menu ---
    help_menu = menubar.addMenu("&Help")
    act_about = QAction("&About", parent)
    act_about.setStatusTip("About this application")
    act_about.triggered.connect(show_about)
    help_menu.addAction(act_about)
