"""Settings hub screen ("Ajustes").

A landing screen reachable from the main menu that lists Settings'
sections as navigation buttons, the same way MainMenuWidget lists its
top-level screens - Ajustes is not itself the métodos-de-pago table, it's
a hub that métodos de pago and reglas de cobro hang off of. See PLAN.md
2.7: "Settings screen... should host: billing-rule management, payment
methods, and possibly..." - i.e. multiple sections, not one screen doing
double duty as both the hub and its only section.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QStyle,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from .metodos_pago_view import show_metodos_pago_view
from .reglas_cobro_view import show_reglas_cobro_view
from ui.styles import SETTINGS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)


class SettingsView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsMenu")
        self.main_window = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # --- Top bar: back button + screen title ------------------------
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

        title = QLabel("Ajustes")
        title.setObjectName("screenTitle")
        top_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        main_layout.addWidget(top_bar)

        # --- Section buttons ----------------------------------------------
        sections_grid = QGridLayout()
        sections_grid.setSpacing(16)
        main_layout.addLayout(sections_grid)
        main_layout.addStretch(1)

        sections = [
            ("💳 Métodos de pago", self.on_open_metodos_pago),
            ("📋 Reglas de cobro", self.on_open_reglas_cobro),
        ]
        columns = 2
        for idx, (label, handler) in enumerate(sections):
            btn = QPushButton(label)
            btn.setMinimumWidth(240)
            btn.setMinimumHeight(56)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            sections_grid.addWidget(btn, idx // columns, idx % columns, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet(SETTINGS_MENU_STYLESHEET)

    def on_back_to_main_menu(self) -> None:
        if self.main_window and hasattr(self.main_window, "_stack") and hasattr(self.main_window, "_home"):
            self.main_window._stack.setCurrentWidget(self.main_window._home)
        else:
            logger.warning("SettingsView.on_back_to_main_menu: no se pudo navegar al menú principal")

    def on_open_metodos_pago(self) -> None:
        if self.main_window is not None:
            show_metodos_pago_view(self.main_window)

    def on_open_reglas_cobro(self) -> None:
        if self.main_window is not None:
            show_reglas_cobro_view(self.main_window)


def show_settings_view(main_window) -> None:
    """Ensure a SettingsView exists in the application's central stack and
    make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    sv = getattr(main_window, "_settings_view", None)
    if sv is None:
        sv = SettingsView(main_window)
        setattr(main_window, "_settings_view", sv)
        main_window._stack.addWidget(sv)

    main_window._stack.setCurrentWidget(sv)
