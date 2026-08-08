"""Dialog for creating or editing a billing rule (ReglaCobro)."""

from __future__ import annotations

import decimal
from typing import Any, Optional

from PySide6.QtCore import QLocale
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class ReglaCobroDialog(QDialog):
    """Modal form for a billing rule's fields.

    Pass `initial_data` (same shape as `get_data()`'s return value) to open
    in "edit" mode; omit it for "new rule" mode.
    """

    def __init__(self, parent: Optional[QWidget] = None, initial_data: Optional[dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar regla de cobro" if initial_data is not None else "Nueva regla de cobro")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        c_locale = QLocale.c()

        self.descripcion_input = QLineEdit(self)
        self.cuota_mensual_input = QLineEdit(self)
        cuota_mensual_validator = QDoubleValidator(0.0, 999999.99, 2, self)
        cuota_mensual_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        cuota_mensual_validator.setLocale(c_locale)
        self.cuota_mensual_input.setValidator(cuota_mensual_validator)
        self.plazo_pago_input = QLineEdit(self)
        self.plazo_pago_input.setValidator(QIntValidator(0, 3650, self))
        self.penalizacion_input = QLineEdit(self)
        penalizacion_validator = QDoubleValidator(0.0, 999999.99, 2, self)
        penalizacion_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        penalizacion_validator.setLocale(c_locale)
        self.penalizacion_input.setValidator(penalizacion_validator)
        self.descuento_input = QLineEdit(self)
        descuento_validator = QDoubleValidator(0.0, 999999.99, 2, self)
        descuento_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        descuento_validator.setLocale(c_locale)
        self.descuento_input.setValidator(descuento_validator)

        form.addRow("Descripción*:", self.descripcion_input)
        form.addRow("Cuota mensual (€):", self.cuota_mensual_input)
        form.addRow("Plazo de pago (días):", self.plazo_pago_input)
        form.addRow("Penalización (€):", self.penalizacion_input)
        form.addRow("Descuento (€):", self.descuento_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if initial_data is not None:
            self._populate(initial_data)

    def _populate(self, data: dict[str, Any]) -> None:
        self.descripcion_input.setText(str(data.get("descripcion") or ""))
        self.cuota_mensual_input.setText(_fmt_number(data.get("cuota_mensual")))
        self.plazo_pago_input.setText(_fmt_number(data.get("plazo_pago")))
        self.penalizacion_input.setText(_fmt_number(data.get("penalizacion")))
        self.descuento_input.setText(_fmt_number(data.get("descuento")))

    def _on_accept(self) -> None:
        if not self.descripcion_input.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "La descripción es obligatoria.")
            return
        self.accept()

    def get_data(self) -> dict[str, Any]:
        """Return the entered rule data as a plain dict ready for persistence."""
        return {
            "descripcion": self.descripcion_input.text().strip(),
            "cuota_mensual": _parse_decimal(self.cuota_mensual_input.text()),
            "plazo_pago": _parse_int(self.plazo_pago_input.text()),
            "penalizacion": _parse_decimal(self.penalizacion_input.text()),
            "descuento": _parse_decimal(self.descuento_input.text()),
        }


def _fmt_number(value: Any) -> str:
    return "" if value is None else str(value)


def _parse_decimal(text: str) -> Optional[decimal.Decimal]:
    text = text.strip()
    if not text:
        return None
    try:
        return decimal.Decimal(text)
    except decimal.InvalidOperation:
        return None


def _parse_int(text: str) -> Optional[int]:
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
