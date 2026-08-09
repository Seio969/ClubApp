"""Tests for AuditLogService (PLAN.md 2.12).

Read-only queries over Log - no CRUD, since Log rows are a permanent
audit trail. Covers the tabla_afectada filter dropdown source, the
socio-display-name resolution, text search, and exact tabla_afectada
filtering.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from database.models import Log, Socio
from features.settings.audit_log.service import AuditLogService


class _FakeModel:
    """Minimal stand-in for QStandardItemModel, no QApplication needed.

    Same shape as test_transactions_service.py's _FakeModel -
    list_logs only calls removeRows/setColumnCount/setRowCount/
    setHorizontalHeaderLabels/appendRow.
    """

    def __init__(self) -> None:
        self.headers: list[str] = []
        self.rows: list[list[str]] = []

    def rowCount(self) -> int:
        return len(self.rows)

    def removeRows(self, start: int, count: int) -> None:
        self.rows = []

    def setColumnCount(self, count: int) -> None:
        pass

    def setRowCount(self, count: int) -> None:
        pass

    def setHorizontalHeaderLabels(self, labels: list[str]) -> None:
        self.headers = list(labels)

    def appendRow(self, items) -> None:
        self.rows.append([item.text() for item in items])


def _make_socio(session, **overrides) -> Socio:
    data = dict(
        numero_socio="1001",
        nombre="Marta",
        apellidos="Fernandez",
        estado="activo",
    )
    data.update(overrides)
    socio = Socio(**data)
    session.add(socio)
    session.flush()
    return socio


def _make_log(session, **overrides) -> Log:
    data = dict(
        id_socio=None,
        accion="crear",
        tabla_afectada="socios",
        id_registro_afectado=1,
        descripcion_cambio="Alta de socio",
        fecha_hora=datetime.datetime(2026, 1, 1, 10, 0, 0),
    )
    data.update(overrides)
    log = Log(**data)
    session.add(log)
    session.flush()
    return log


class TestListTablasAfectadas:
    def test_returns_distinct_non_empty_values(self, test_engine):
        with Session(test_engine) as session:
            _make_log(session, tabla_afectada="socios")
            _make_log(session, tabla_afectada="socios")
            _make_log(session, tabla_afectada="metodos_pago")
            _make_log(session, tabla_afectada=None)
            session.commit()

        tablas = AuditLogService().list_tablas_afectadas()

        assert tablas == ["metodos_pago", "socios"]


class TestListLogs:
    def test_no_model_returns_zero(self, test_engine):
        assert AuditLogService().list_logs("") == 0

    def test_resolves_socio_display_name(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session, nombre="Jorge", apellidos="Dominguez")
            _make_log(session, id_socio=socio.id_socio, tabla_afectada="socios")
            session.commit()

        model = _FakeModel()
        added = AuditLogService().list_logs("", model=model)

        assert added == 1
        assert model.rows[0][2] == "Jorge Dominguez"

    def test_blank_socio_label_when_not_attributed(self, test_engine):
        with Session(test_engine) as session:
            _make_log(session, id_socio=None, tabla_afectada="reset")
            session.commit()

        model = _FakeModel()
        AuditLogService().list_logs("", model=model)

        assert model.rows[0][2] == ""

    def test_filters_by_tabla_afectada(self, test_engine):
        with Session(test_engine) as session:
            _make_log(session, tabla_afectada="socios")
            _make_log(session, tabla_afectada="metodos_pago")
            session.commit()

        model = _FakeModel()
        added = AuditLogService().list_logs("", tabla_afectada="metodos_pago", model=model)

        assert added == 1
        assert model.rows[0][4] == "metodos_pago"

    def test_search_matches_socio_accion_or_descripcion(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session, nombre="Jorge", apellidos="Dominguez")
            _make_log(session, id_socio=socio.id_socio, accion="crear", descripcion_cambio="Alta de socio")
            _make_log(session, id_socio=None, accion="reset_completo", descripcion_cambio="Reinicio total")
            session.commit()

        model = _FakeModel()
        added = AuditLogService().list_logs("jorge", model=model)

        assert added == 1
        assert "Jorge" in model.rows[0][2]

    def test_search_is_accent_insensitive(self, test_engine):
        with Session(test_engine) as session:
            _make_log(session, accion="reset_completo", descripcion_cambio="Reinicio de la base de datos")
            session.commit()

        model = _FakeModel()
        added = AuditLogService().list_logs("reinicio", model=model)

        assert added == 1

    def test_orders_most_recent_first(self, test_engine):
        with Session(test_engine) as session:
            _make_log(session, descripcion_cambio="primero", fecha_hora=datetime.datetime(2026, 1, 1))
            _make_log(session, descripcion_cambio="segundo", fecha_hora=datetime.datetime(2026, 2, 1))
            session.commit()

        model = _FakeModel()
        AuditLogService().list_logs("", model=model)

        assert [r[6] for r in model.rows] == ["segundo", "primero"]
