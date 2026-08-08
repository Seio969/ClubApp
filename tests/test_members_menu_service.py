"""Tests for MembersMenuService.search_members (menu_service.py).

search_members used to be a demo/FIXME placeholder that fabricated a single
row; it now runs a real query over Socio via database.session.get_session(),
which the test_engine fixture points at an isolated per-test SQLite DB.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from database.models import Socio
from features.members.menu_service import MembersMenuService


class _FakeModel:
    """Minimal stand-in for QStandardItemModel, no PySide6/QApplication needed.

    _populate_model only calls removeRows/setColumnCount/setRowCount/
    setHorizontalHeaderLabels/appendRow - QStandardItem itself is still real
    Qt, but constructing QStandardItem objects doesn't require a running
    QApplication.
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


def _add_socio(engine, **overrides) -> None:
    data = dict(
        numero_socio="1001",
        nombre="Marta",
        apellidos="Fernandez Ruiz",
        telefono="612345678",
        email="marta@example.com",
        fecha_alta=datetime.date(2024, 1, 15),
        estado="activo",
        observaciones=None,
    )
    data.update(overrides)
    with Session(engine) as session:
        session.add(Socio(**data))
        session.commit()


class TestSearchMembers:
    def test_no_model_returns_zero(self, test_engine):
        service = MembersMenuService()

        assert service.search_members("marta", None) == 0

    def test_empty_text_returns_all_members(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta")
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("", model)

        assert added == 2
        assert len(model.rows) == 2

    def test_matches_by_nombre(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta", email="marta@example.com")
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge", email="jorge@example.com")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("Marta", model)

        assert added == 1
        assert model.rows[0][2] == "Marta"  # nombre column

    def test_matches_by_apellidos(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta", apellidos="Fernandez Ruiz")
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge", apellidos="Dominguez Pena")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("Dominguez", model)

        assert added == 1
        assert model.rows[0][3] == "Dominguez Pena"

    def test_matches_by_numero_socio(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta")
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("1002", model)

        assert added == 1
        assert model.rows[0][1] == "1002"

    def test_matches_by_email(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta", email="marta@example.com")
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge", email="jorge@other.com")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("other.com", model)

        assert added == 1
        assert model.rows[0][5] == "jorge@other.com"

    def test_search_is_case_insensitive(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("MARTA", model)

        assert added == 1

    def test_search_is_accent_insensitive(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Álvaro")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("Alvaro", model)

        assert added == 1

    def test_no_match_returns_zero_and_empty_model(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("Nonexistent", model)

        assert added == 0
        assert model.rows == []

    def test_limit_restricts_row_count(self, test_engine):
        for i in range(3):
            _add_socio(test_engine, numero_socio=f"100{i}", nombre=f"Nombre{i}")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("", model, limit=1)

        assert added == 1

    def test_limit_zero_means_no_limit(self, test_engine):
        for i in range(3):
            _add_socio(test_engine, numero_socio=f"100{i}", nombre=f"Nombre{i}")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("", model, limit=0)

        assert added == 3

    def test_inactive_members_are_still_matched(self, test_engine):
        # estado-aware filtering/display doesn't exist yet (PLAN.md 2.2) -
        # search must not silently hide deactivated members.
        _add_socio(test_engine, numero_socio="1001", nombre="Marta", estado="inactivo")
        service = MembersMenuService()
        model = _FakeModel()

        added = service.search_members("Marta", model)

        assert added == 1
        assert model.rows[0][7] == "inactivo"  # estado column

    def test_es_titular_column_shows_si_no(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta", es_titular=True)
        _add_socio(test_engine, numero_socio="1002", nombre="Jorge", es_titular=False)
        service = MembersMenuService()
        model = _FakeModel()

        service.search_members("", model)

        rows_by_nombre = {row[2]: row[8] for row in model.rows}
        assert rows_by_nombre == {"Marta": "Sí", "Jorge": "No"}

    def test_populates_headers_with_socio_columns(self, test_engine):
        _add_socio(test_engine, numero_socio="1001", nombre="Marta")
        service = MembersMenuService()
        model = _FakeModel()

        service.search_members("", model)

        assert model.headers == [
            "id_socio",
            "numero_socio",
            "nombre",
            "apellidos",
            "telefono",
            "email",
            "fecha_alta",
            "estado",
            "es_titular",
            "observaciones",
        ]
