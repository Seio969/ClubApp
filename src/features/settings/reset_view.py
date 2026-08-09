"""Database reset screen - one section reachable from the Settings hub.

PLAN.md 2.15, decided (safety): a very safe confirmation flow, not a
single dismissable dialog - each action requires typing an exact phrase
into a text field before its button even enables, plus a final Yes/No
prompt, and the two actions are visually distinguished (wording + color)
so they can't be mis-clicked for each other.
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
    QGroupBox,
    QStyle,
    QMessageBox,
)
from PySide6.QtCore import Qt

from .reset_service import ResetService
from ui.styles import SETTINGS_MENU_STYLESHEET
from utils.logger import get_logger

logger = get_logger(__name__)

_PARCIAL_PHRASE = "REINICIAR"
_COMPLETO_PHRASE = "BORRAR TODO"


class ResetView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsMenu")
        self.main_window = parent
        self._service = ResetService()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(14)

        # --- Top bar: back button (to the Settings hub) + screen title --
        top_bar = QWidget(self)
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 6, 6, 6)

        back_button = QPushButton("Volver")
        back_button.setObjectName("backButton")
        back_button.setToolTip("Volver a Ajustes")
        back_button.setMaximumWidth(120)
        back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        back_button.clicked.connect(self.on_back_to_settings)
        top_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Restablecer base de datos")
        title.setObjectName("screenTitle")
        top_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        top_layout.addStretch(1)

        main_layout.addWidget(top_bar)

        warning = QLabel("⚠️ Estas acciones no se pueden deshacer.")
        warning.setStyleSheet("font-weight: 600; color: #A1382F;")
        main_layout.addWidget(warning)

        # --- Reinicio parcial ------------------------------------------
        parcial_box = QGroupBox("Reinicio parcial")
        parcial_box.setStyleSheet("QGroupBox { border: 1px solid #B8862B; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { color: #B8862B; font-weight: 600; }")
        parcial_layout = QVBoxLayout(parcial_box)

        parcial_desc = QLabel(
            "Elimina transacciones, saldos y periodos. Los socios, métodos de pago "
            "y reglas de cobro se conservan."
        )
        parcial_desc.setWordWrap(True)
        parcial_layout.addWidget(parcial_desc)

        parcial_layout.addWidget(QLabel(f"Escriba «{_PARCIAL_PHRASE}» para habilitar el botón:"))
        self.parcial_input = QLineEdit(parcial_box)
        self.parcial_input.textChanged.connect(self._update_parcial_button)
        parcial_layout.addWidget(self.parcial_input)

        self.parcial_button = QPushButton("Confirmar reinicio parcial")
        self.parcial_button.setEnabled(False)
        self.parcial_button.setStyleSheet(
            "QPushButton { background-color: #B8862B; color: #ffffff; font-weight: 600; padding: 8px; }"
            "QPushButton:disabled { background-color: #d8c9a8; color: #f0ead9; }"
        )
        self.parcial_button.clicked.connect(self.on_confirm_parcial)
        parcial_layout.addWidget(self.parcial_button)

        main_layout.addWidget(parcial_box)

        # --- Reinicio completo -------------------------------------------
        completo_box = QGroupBox("Reinicio completo")
        completo_box.setStyleSheet("QGroupBox { border: 1px solid #A1382F; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { color: #A1382F; font-weight: 600; }")
        completo_layout = QVBoxLayout(completo_box)

        completo_desc = QLabel(
            "Elimina TODOS los datos: socios, transacciones, saldos, periodos, métodos de "
            "pago, reglas de cobro e historial de auditoría. Los métodos de pago fijos se "
            "vuelven a crear automáticamente."
        )
        completo_desc.setWordWrap(True)
        completo_layout.addWidget(completo_desc)

        completo_layout.addWidget(QLabel(f"Escriba «{_COMPLETO_PHRASE}» para habilitar el botón:"))
        self.completo_input = QLineEdit(completo_box)
        self.completo_input.textChanged.connect(self._update_completo_button)
        completo_layout.addWidget(self.completo_input)

        self.completo_button = QPushButton("Confirmar reinicio completo")
        self.completo_button.setEnabled(False)
        self.completo_button.setStyleSheet(
            "QPushButton { background-color: #A1382F; color: #ffffff; font-weight: 600; padding: 8px; }"
            "QPushButton:disabled { background-color: #e0c3bf; color: #f5eae9; }"
        )
        self.completo_button.clicked.connect(self.on_confirm_completo)
        completo_layout.addWidget(self.completo_button)

        main_layout.addWidget(completo_box)
        main_layout.addStretch(1)

        self.setStyleSheet(SETTINGS_MENU_STYLESHEET)

    def _update_parcial_button(self, text: str) -> None:
        self.parcial_button.setEnabled(text.strip() == _PARCIAL_PHRASE)

    def _update_completo_button(self, text: str) -> None:
        self.completo_button.setEnabled(text.strip() == _COMPLETO_PHRASE)

    def on_back_to_settings(self) -> None:
        if self.main_window and hasattr(self.main_window, "_stack") and hasattr(self.main_window, "_settings_view"):
            self.main_window._stack.setCurrentWidget(self.main_window._settings_view)
        else:
            logger.warning("ResetView.on_back_to_settings: no se pudo navegar a Ajustes")

    def on_confirm_parcial(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar reinicio parcial",
            "¿Eliminar todas las transacciones, saldos y periodos?\n\n"
            "Los socios, métodos de pago y reglas de cobro se conservarán. "
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok = self._service.scoped_reset()
        self.parcial_input.clear()
        if ok:
            QMessageBox.information(self, "Reinicio parcial", "Transacciones, saldos y periodos eliminados.")
        else:
            QMessageBox.critical(self, "Error", "No se pudo completar el reinicio parcial.")

    def on_confirm_completo(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar reinicio completo",
            "¿Borrar TODOS los datos de la base de datos?\n\n"
            "Esto incluye socios, transacciones, saldos, periodos, métodos de pago, "
            "reglas de cobro e historial de auditoría. Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok = self._service.full_reset()
        self.completo_input.clear()
        if ok:
            QMessageBox.information(self, "Reinicio completo", "Base de datos reiniciada por completo.")
        else:
            QMessageBox.critical(self, "Error", "No se pudo completar el reinicio.")


def show_reset_view(main_window) -> None:
    """Ensure a ResetView exists in the application's central stack and
    make it the current widget - same singleton pattern as
    features.members.menu_view.show_members_view.
    """
    if main_window is None:
        raise ValueError("main_window is required")

    rv = getattr(main_window, "_reset_view", None)
    if rv is None:
        rv = ResetView(main_window)
        main_window._reset_view = rv
        main_window._stack.addWidget(rv)

    main_window._stack.setCurrentWidget(rv)
