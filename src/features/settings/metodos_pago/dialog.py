"""Dialog for creating or renaming a custom payment method (MetodoPago)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class MetodoPagoDialog(QDialog):
    """Modal form for a payment method's name.

    Pass `initial_nombre` to open in "rename" mode; omit it for "new
    method" mode. Fixed methods should never reach this dialog in rename
    mode - MetodosPagoToolBar checks that before opening it.
    """

    def __init__(self, parent: Optional[QWidget] = None, initial_nombre: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Renombrar método de pago" if initial_nombre is not None else "Nuevo método de pago")
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombre_input = QLineEdit(self)
        if initial_nombre is not None:
            self.nombre_input.setText(initial_nombre)
        form.addRow("Nombre*:", self.nombre_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "El nombre es obligatorio.")
            return
        self.accept()

    def get_nombre(self) -> str:
        return self.nombre_input.text().strip()
