"""Dialog for registering a transaction (cargo/pago/reembolso).

Shared by both entry points decided in PLAN.md 2.4: the Members toolbar's
"Registrar" shortcut (which pre-fills and locks the socio field via
`preset_socio`) and the standalone Transacciones screen's "Nuevo
movimiento" action (which leaves the socio field open for search/select).
"""

from __future__ import annotations

import datetime
import decimal
from typing import Any, Optional

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .service import TIPOS_TRANSACCION, TransactionsService


class _PeriodoRapidoDialog(QDialog):
    """Tiny inline form to create a período from within TransactionDialog.

    Only asks for nombre + fecha_inicio (PLAN.md 2.4 decision) - fecha_fin
    is derived by TransactionsService.create_periodo_rapido.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo período")
        self.setModal(True)
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.nombre_input = QLineEdit(self)
        self.fecha_inicio_input = QDateEdit(self)
        self.fecha_inicio_input.setCalendarPopup(True)
        self.fecha_inicio_input.setDate(QDate.currentDate())
        form.addRow("Nombre*:", self.nombre_input)
        form.addRow("Fecha de inicio*:", self.fecha_inicio_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self.nombre_input.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "El nombre del período es obligatorio.")
            return
        self.accept()

    def get_data(self) -> dict[str, Any]:
        qdate = self.fecha_inicio_input.date()
        return {
            "nombre": self.nombre_input.text().strip(),
            "fecha_inicio": datetime.date(qdate.year(), qdate.month(), qdate.day()),
        }


class TransactionDialog(QDialog):
    """Modal form for registering a single transaction.

    Pass `preset_socio` (a dict with id_socio/numero_socio/nombre/apellidos,
    the shape TransactionsService.list_socios_activos() returns per row) to
    pre-fill and lock the socio field - the Members-toolbar "Registrar" path
    does this; the standalone Transacciones screen omits it and leaves the
    socio field open for search/select.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        service: Optional[TransactionsService] = None,
        preset_socio: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self.service = service or TransactionsService()
        self.setWindowTitle("Registrar movimiento")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        c_locale = QLocale.c()

        # --- Socio picker: searchable combo of active socios -------------
        # Defaults to titulares only (PLAN.md 2.17), but the completer's
        # search list covers every active socio in a numero_socio group that
        # *has* a titular - selecting one dynamically adds it as a combo
        # item (see _on_socio_completer_activated). Groups with no titular
        # assigned yet are excluded entirely (blocked until an admin
        # assigns one via Members/Ajustes).
        self.socio_input = QComboBox(self)
        self.socio_input.setEditable(True)
        self.socio_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._socios = self.service.list_socios_activos()
        numeros_con_titular = {s["numero_socio"] for s in self._socios if s.get("es_titular")}
        self._selectable_socios = [s for s in self._socios if s["numero_socio"] in numeros_con_titular]
        self._titulares = [s for s in self._selectable_socios if s.get("es_titular")]
        for socio in self._titulares:
            label = f"{socio['numero_socio']} · {socio['nombre']} {socio['apellidos']}"
            self.socio_input.addItem(label, socio)
        all_labels = [
            f"{s['numero_socio']} · {s['nombre']} {s['apellidos']}" for s in self._selectable_socios
        ]
        completer = QCompleter(all_labels, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.activated.connect(self._on_socio_completer_activated)
        self.socio_input.setCompleter(completer)
        form.addRow("Socio*:", self.socio_input)

        # --- Tipo ----------------------------------------------------------
        self.tipo_input = QComboBox(self)
        self.tipo_input.addItems(list(TIPOS_TRANSACCION))
        form.addRow("Tipo*:", self.tipo_input)

        # --- Monto -----------------------------------------------------------
        self.monto_input = QLineEdit(self)
        monto_validator = QDoubleValidator(0.01, 999999.99, 2, self)
        monto_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        monto_validator.setLocale(c_locale)
        self.monto_input.setValidator(monto_validator)
        form.addRow("Monto (€)*:", self.monto_input)

        # --- Método de pago ------------------------------------------------
        self.metodo_input = QComboBox(self)
        self._metodos = self.service.list_metodos_pago_activos()
        for metodo in self._metodos:
            self.metodo_input.addItem(metodo["nombre"], metodo)
        form.addRow("Método de pago*:", self.metodo_input)

        # --- Período (+ inline quick-create) --------------------------------
        periodo_row = QWidget(self)
        periodo_row_layout = QHBoxLayout(periodo_row)
        periodo_row_layout.setContentsMargins(0, 0, 0, 0)
        self.periodo_input = QComboBox(periodo_row)
        self._load_periodos()
        periodo_row_layout.addWidget(self.periodo_input, 1)
        btn_nuevo_periodo = QPushButton("Nuevo…", periodo_row)
        btn_nuevo_periodo.setToolTip("Crear un período nuevo")
        btn_nuevo_periodo.clicked.connect(self._on_nuevo_periodo)
        periodo_row_layout.addWidget(btn_nuevo_periodo, 0)
        form.addRow("Período*:", periodo_row)

        # --- Fecha -----------------------------------------------------------
        self.fecha_input = QDateEdit(self)
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDate(QDate.currentDate())
        form.addRow("Fecha:", self.fecha_input)

        # --- Referencia --------------------------------------------------
        self.referencia_input = QLineEdit(self)
        form.addRow("Referencia:", self.referencia_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if preset_socio is not None:
            self._select_preset_socio(preset_socio)

    def _on_socio_completer_activated(self, text: str) -> None:
        """Handle picking a socio via the completer's search results.

        The combo only starts populated with titulares; picking a
        non-titular match (still allowed - see PLAN.md 2.17, "shouldn't
        hard-block that") adds it as a combo item on the fly so
        currentData() resolves correctly.
        """
        idx = self.socio_input.findText(text)
        if idx >= 0:
            self.socio_input.setCurrentIndex(idx)
            return
        for socio in self._selectable_socios:
            label = f"{socio['numero_socio']} · {socio['nombre']} {socio['apellidos']}"
            if label == text:
                self.socio_input.addItem(label, socio)
                self.socio_input.setCurrentIndex(self.socio_input.count() - 1)
                return

    def _load_periodos(self, select_id: Optional[int] = None) -> None:
        self.periodo_input.clear()
        self._periodos = self.service.list_periodos()
        select_index = 0
        for idx, periodo in enumerate(self._periodos):
            label = f"{periodo['nombre']} ({periodo['estado']})"
            self.periodo_input.addItem(label, periodo)
            if select_id is not None and periodo["id_periodo"] == select_id:
                select_index = idx
        if self._periodos:
            self.periodo_input.setCurrentIndex(select_index)

    def _on_nuevo_periodo(self) -> None:
        dialog = _PeriodoRapidoDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        new_id = self.service.create_periodo_rapido(data["nombre"], data["fecha_inicio"])
        if new_id is None:
            QMessageBox.critical(self, "Error", "No se pudo crear el período.")
            return
        self._load_periodos(select_id=new_id)

    def _select_preset_socio(self, preset_socio: dict[str, Any]) -> None:
        target_numero = preset_socio.get("numero_socio")
        for idx in range(self.socio_input.count()):
            data = self.socio_input.itemData(idx)
            if data is not None and data.get("numero_socio") == target_numero:
                self.socio_input.setCurrentIndex(idx)
                break
        else:
            # The preset socio isn't in the active-socios list (e.g. it was
            # deactivated between selection and dialog open) - add it so the
            # field still shows something sensible, then select it.
            label = (
                f"{preset_socio.get('numero_socio')} · "
                f"{preset_socio.get('nombre', '')} {preset_socio.get('apellidos', '')}"
            )
            self.socio_input.addItem(label, preset_socio)
            self.socio_input.setCurrentIndex(self.socio_input.count() - 1)
        self.socio_input.setEnabled(False)

    def _on_accept(self) -> None:
        if self.socio_input.currentData() is None:
            QMessageBox.warning(self, "Datos incompletos", "Seleccione un socio válido de la lista.")
            return
        if self.metodo_input.currentData() is None:
            QMessageBox.warning(self, "Datos incompletos", "Seleccione un método de pago.")
            return
        if self.periodo_input.currentData() is None:
            QMessageBox.warning(self, "Datos incompletos", "Seleccione o cree un período.")
            return
        if not self.monto_input.hasAcceptableInput() or not self.monto_input.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "Introduzca un monto válido mayor que 0.")
            return
        self.accept()

    def get_data(self) -> dict[str, Any]:
        """Return the entered transaction data, ready for
        TransactionsService.add_transaction().
        """
        socio = self.socio_input.currentData()
        metodo = self.metodo_input.currentData()
        periodo = self.periodo_input.currentData()
        qdate = self.fecha_input.date()
        return {
            "numero_socio": socio.get("numero_socio"),
            "id_socio_log": socio.get("id_socio"),
            "id_periodo": periodo.get("id_periodo"),
            "id_metodo": metodo.get("id_metodo"),
            "tipo": self.tipo_input.currentText(),
            "monto": decimal.Decimal(self.monto_input.text().replace(",", ".")),
            "fecha": datetime.date(qdate.year(), qdate.month(), qdate.day()),
            "referencia": self.referencia_input.text().strip() or None,
        }
