"""Tests for the "titular" (primary holder) per numero_socio feature (PLAN.md
2.17): Socio.es_titular, MembersService's auto-unset-other-titular /
new-numero-requires-titular rules, and the transactions-side consumers
(TransactionsService.has_titular, list_socios_activos' es_titular flag,
list_transactions' titular-preferring display name).
"""

from __future__ import annotations

import datetime
import decimal

from sqlalchemy.orm import Session

from database.models import Log, Periodo, Socio, Transaccion
from features.members.toolbar_service import MembersService
from features.transactions.service import TransactionsService


def _valid_socio_data(**overrides) -> dict:
    data = dict(
        numero_socio="1001",
        nombre="Marta",
        apellidos="Fernandez Ruiz",
        telefono=None,
        email=None,
        fecha_alta=datetime.date(2024, 1, 15),
        estado="activo",
        observaciones=None,
    )
    data.update(overrides)
    return data


class TestAddMemberTitular:
    def test_first_member_of_a_new_numero_socio_becomes_titular(self, test_engine):
        service = MembersService()

        new_id = service.add_member(_valid_socio_data(es_titular=False))

        with Session(test_engine) as session:
            socio = session.get(Socio, new_id)
            assert socio.es_titular is True

    def test_second_member_of_same_numero_defaults_to_not_titular(self, test_engine):
        service = MembersService()
        service.add_member(_valid_socio_data(nombre="Marta"))

        second_id = service.add_member(_valid_socio_data(nombre="Jose", es_titular=False))

        with Session(test_engine) as session:
            socio = session.get(Socio, second_id)
            assert socio.es_titular is False

    def test_marking_new_member_as_titular_unsets_previous_titular(self, test_engine):
        service = MembersService()
        first_id = service.add_member(_valid_socio_data(nombre="Marta"))

        second_id = service.add_member(_valid_socio_data(nombre="Jose", es_titular=True))

        with Session(test_engine) as session:
            first = session.get(Socio, first_id)
            second = session.get(Socio, second_id)
            assert first.es_titular is False
            assert second.es_titular is True

    def test_titular_swap_records_cambio_titular_log(self, test_engine):
        service = MembersService()
        service.add_member(_valid_socio_data(nombre="Marta"))

        second_id = service.add_member(_valid_socio_data(nombre="Jose", es_titular=True))

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="cambio_titular").all()
            assert len(logs) == 1
            assert logs[0].id_socio == second_id
            assert "Marta" in logs[0].descripcion_cambio
            assert "Jose" in logs[0].descripcion_cambio


class TestUpdateMemberTitular:
    def test_promoting_a_member_unsets_the_other_titular(self, test_engine):
        service = MembersService()
        first_id = service.add_member(_valid_socio_data(nombre="Marta"))
        second_id = service.add_member(_valid_socio_data(nombre="Jose", es_titular=False))

        ok = service.update_member(second_id, _valid_socio_data(nombre="Jose", es_titular=True))

        assert ok is True
        with Session(test_engine) as session:
            first = session.get(Socio, first_id)
            second = session.get(Socio, second_id)
            assert first.es_titular is False
            assert second.es_titular is True

    def test_re_saving_the_current_titular_as_titular_is_a_no_op(self, test_engine):
        service = MembersService()
        first_id = service.add_member(_valid_socio_data(nombre="Marta"))

        ok = service.update_member(first_id, _valid_socio_data(nombre="Marta Actualizada", es_titular=True))

        assert ok is True
        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="cambio_titular").all()
            assert logs == []


class TestGetTitular:
    def test_returns_none_when_no_titular_set(self, test_engine):
        service = MembersService()
        service.add_member(_valid_socio_data(nombre="Marta", es_titular=False))
        # Force the group into a titular-less state, as if it predated the
        # feature (PLAN.md 2.17's "existing data" case).
        with Session(test_engine) as session:
            session.query(Socio).update({Socio.es_titular: False})
            session.commit()

        assert service.get_titular("1001") is None

    def test_returns_the_titular_dict(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data(nombre="Marta"))

        titular = service.get_titular("1001")

        assert titular == {
            "id_socio": new_id,
            "numero_socio": "1001",
            "nombre": "Marta",
            "apellidos": "Fernandez Ruiz",
        }


def _make_socio(session, **overrides) -> Socio:
    data = dict(
        numero_socio="1001",
        nombre="Marta",
        apellidos="Fernandez",
        estado="activo",
        es_titular=False,
    )
    data.update(overrides)
    socio = Socio(**data)
    session.add(socio)
    session.flush()
    return socio


class TestTransactionsServiceHasTitular:
    def test_true_when_a_socio_in_the_group_is_titular(self, test_engine):
        with Session(test_engine) as session:
            _make_socio(session, es_titular=True)
            session.commit()

        assert TransactionsService().has_titular("1001") is True

    def test_false_when_no_titular_assigned(self, test_engine):
        with Session(test_engine) as session:
            _make_socio(session, es_titular=False)
            session.commit()

        assert TransactionsService().has_titular("1001") is False

    def test_false_for_unknown_numero_socio(self, test_engine):
        assert TransactionsService().has_titular("9999") is False


class TestListSociosActivosIncludesTitular:
    def test_es_titular_flag_is_included_per_row(self, test_engine):
        with Session(test_engine) as session:
            _make_socio(session, numero_socio="1001", nombre="Marta", es_titular=True)
            _make_socio(session, numero_socio="1002", nombre="Jorge", es_titular=False)
            session.commit()

        rows = {r["nombre"]: r["es_titular"] for r in TransactionsService().list_socios_activos()}

        assert rows == {"Marta": True, "Jorge": False}


class _FakeModel:
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


class TestListTransactionsPrefersTitularName:
    def test_shows_the_titular_name_even_if_created_after_a_non_titular_sibling(self, test_engine):
        with Session(test_engine) as session:
            # Jorge is added first (lower id_socio) but Marta is the titular -
            # the display name must prefer Marta, not "first by id".
            _make_socio(session, numero_socio="1001", nombre="Jorge", apellidos="Fernandez", es_titular=False)
            _make_socio(session, numero_socio="1001", nombre="Marta", apellidos="Fernandez", es_titular=True)
            periodo = Periodo(
                nombre="Enero 2026",
                fecha_inicio=datetime.date(2026, 1, 1),
                fecha_fin=datetime.date(2026, 1, 31),
                estado="abierto",
            )
            session.add(periodo)
            session.flush()
            session.add(
                Transaccion(
                    numero_socio="1001",
                    id_periodo=periodo.id_periodo,
                    tipo="pago",
                    monto=decimal.Decimal("45.00"),
                    fecha=datetime.date(2026, 1, 5),
                )
            )
            session.commit()

        model = _FakeModel()
        TransactionsService().list_transactions("", model=model)

        assert "Marta" in model.rows[0][2]
        assert "Jorge" not in model.rows[0][2]
