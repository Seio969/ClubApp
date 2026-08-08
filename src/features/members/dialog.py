"""Dialog for creating a new member (Socio)."""

from __future__ import annotations

import datetime
from typing import Any, Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MemberDialog(QDialog):
    """Modal form for entering a new member's data, or editing an existing one.

    Pass `initial_data` (same shape as `get_data()`'s return value) to open
    the dialog pre-filled in "edit" mode; omit it for "new member" mode.
    """

    def __init__(self, parent: Optional[QWidget] = None, initial_data: Optional[dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar miembro" if initial_data is not None else "Nuevo miembro")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.numero_socio_input = QLineEdit(self)
        self.nombre_input = QLineEdit(self)
        self.apellidos_input = QLineEdit(self)
        self.telefono_input = QLineEdit(self)
        self.email_input = QLineEdit(self)
        self.fecha_alta_input = QDateEdit(self)
        self.fecha_alta_input.setCalendarPopup(True)
        self.fecha_alta_input.setDate(QDate.currentDate())
        self.estado_input = QComboBox(self)
        self.estado_input.addItems(["activo", "inactivo"])
        self.observaciones_input = QTextEdit(self)
        self.observaciones_input.setFixedHeight(60)

        form.addRow("Número de socio*:", self.numero_socio_input)
        form.addRow("Nombre*:", self.nombre_input)
        form.addRow("Apellidos*:", self.apellidos_input)
        form.addRow("Teléfono:", self.telefono_input)
        form.addRow("Email:", self.email_input)
        form.addRow("Fecha de alta:", self.fecha_alta_input)
        form.addRow("Estado:", self.estado_input)
        form.addRow("Observaciones:", self.observaciones_input)

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
        """Fill the form fields from `data` (edit mode)."""
        self.numero_socio_input.setText(str(data.get("numero_socio") or ""))
        self.nombre_input.setText(str(data.get("nombre") or ""))
        self.apellidos_input.setText(str(data.get("apellidos") or ""))
        self.telefono_input.setText(str(data.get("telefono") or ""))
        self.email_input.setText(str(data.get("email") or ""))

        fecha_alta = data.get("fecha_alta")
        if isinstance(fecha_alta, datetime.date):
            self.fecha_alta_input.setDate(QDate(fecha_alta.year, fecha_alta.month, fecha_alta.day))

        estado = data.get("estado")
        if estado:
            idx = self.estado_input.findText(str(estado))
            if idx >= 0:
                self.estado_input.setCurrentIndex(idx)

        self.observaciones_input.setPlainText(str(data.get("observaciones") or ""))

    def _on_accept(self) -> None:
        if (
            not self.numero_socio_input.text().strip()
            or not self.nombre_input.text().strip()
            or not self.apellidos_input.text().strip()
        ):
            QMessageBox.warning(
                self, "Datos incompletos", "Número de socio, nombre y apellidos son obligatorios."
            )
            return
        self.accept()

    def get_data(self) -> dict[str, Any]:
        """Return the entered member data as a plain dict ready for persistence."""
        qdate = self.fecha_alta_input.date()
        return {
            "numero_socio": self.numero_socio_input.text().strip(),
            "nombre": self.nombre_input.text().strip(),
            "apellidos": self.apellidos_input.text().strip(),
            "telefono": self.telefono_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "fecha_alta": datetime.date(qdate.year(), qdate.month(), qdate.day()),
            "estado": self.estado_input.currentText(),
            "observaciones": self.observaciones_input.toPlainText().strip() or None,
        }
