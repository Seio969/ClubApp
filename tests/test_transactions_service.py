"""Tests for TransactionsService (PLAN.md 2.4).

Covers the lookup helpers that back TransactionDialog's dropdowns, the
minimal período quick-create, and add_transaction's persistence + audit
log. Integrity validation (refund-without-payment, duplicate detection)
and balance recalculation get their own tests once those build steps land.
"""

from __future__ import annotations

import datetime
import decimal

from sqlalchemy.orm import Session

from database.models import Log, MetodoPago, Periodo, Socio, Transaccion
from features.transactions.service import TransactionsService


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


def _make_metodo(session, **overrides) -> MetodoPago:
    data = dict(nombre="EFECTIVO", estado="activo")
    data.update(overrides)
    metodo = MetodoPago(**data)
    session.add(metodo)
    session.flush()
    return metodo


class _FakeModel:
    """Minimal stand-in for QStandardItemModel, no QApplication needed.

    Same shape as test_members_menu_service.py's _FakeModel - list_transactions
    only calls removeRows/setColumnCount/setRowCount/
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


def _make_periodo(session, **overrides) -> Periodo:
    data = dict(
        nombre="Enero 2026",
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 1, 31),
        estado="abierto",
    )
    data.update(overrides)
    periodo = Periodo(**data)
    session.add(periodo)
    session.flush()
    return periodo


class TestListSociosActivos:
    def test_only_returns_active_socios(self, test_engine):
        with Session(test_engine) as session:
            _make_socio(session, numero_socio="1001", nombre="Marta")
            _make_socio(session, numero_socio="1002", nombre="Jorge", estado="inactivo")
            session.commit()

        rows = TransactionsService().list_socios_activos()

        assert [r["nombre"] for r in rows] == ["Marta"]


class TestListMetodosPagoActivos:
    def test_only_returns_active_metodos(self, test_engine):
        with Session(test_engine) as session:
            _make_metodo(session, nombre="EFECTIVO", estado="activo")
            _make_metodo(session, nombre="INACTIVO", estado="inactivo")
            session.commit()

        rows = TransactionsService().list_metodos_pago_activos()

        assert [r["nombre"] for r in rows] == ["EFECTIVO"]


class TestListPeriodos:
    def test_orders_most_recent_first(self, test_engine):
        with Session(test_engine) as session:
            _make_periodo(session, nombre="Enero", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
            _make_periodo(session, nombre="Febrero", fecha_inicio=datetime.date(2026, 2, 1), fecha_fin=datetime.date(2026, 2, 28))
            session.commit()

        rows = TransactionsService().list_periodos()

        assert [r["nombre"] for r in rows] == ["Febrero", "Enero"]


class TestCreatePeriodoRapido:
    def test_derives_fecha_fin_one_month_minus_a_day(self, test_engine):
        service = TransactionsService()

        new_id = service.create_periodo_rapido("Marzo 2026", datetime.date(2026, 3, 1))

        assert new_id is not None
        with Session(test_engine) as session:
            periodo = session.get(Periodo, new_id)
            assert periodo.nombre == "Marzo 2026"
            assert periodo.fecha_inicio == datetime.date(2026, 3, 1)
            assert periodo.fecha_fin == datetime.date(2026, 3, 31)
            assert periodo.estado == "abierto"

    def test_handles_end_of_year_rollover(self, test_engine):
        service = TransactionsService()

        new_id = service.create_periodo_rapido("Diciembre 2026", datetime.date(2026, 12, 1))

        with Session(test_engine) as session:
            periodo = session.get(Periodo, new_id)
            assert periodo.fecha_fin == datetime.date(2026, 12, 31)

    def test_requires_nombre(self, test_engine):
        service = TransactionsService()

        assert service.create_periodo_rapido("", datetime.date(2026, 1, 1)) is None

    def test_creates_audit_log_row(self, test_engine):
        service = TransactionsService()

        new_id = service.create_periodo_rapido("Marzo 2026", datetime.date(2026, 3, 1))

        with Session(test_engine) as session:
            logs = session.query(Log).all()
            assert len(logs) == 1
            assert logs[0].tabla_afectada == "periodo"
            assert logs[0].id_registro_afectado == new_id
            assert logs[0].id_socio is None


class TestAddTransaction:
    def _base_data(self, session) -> dict:
        socio = _make_socio(session)
        metodo = _make_metodo(session)
        periodo = _make_periodo(session)
        session.commit()
        return {
            "numero_socio": socio.numero_socio,
            "id_socio_log": socio.id_socio,
            "id_periodo": periodo.id_periodo,
            "id_metodo": metodo.id_metodo,
            "tipo": "pago",
            "monto": decimal.Decimal("45.00"),
            "fecha": datetime.date(2026, 1, 5),
            "referencia": "Pago cuota enero",
        }

    def test_persists_and_returns_new_id(self, test_engine):
        with Session(test_engine) as session:
            data = self._base_data(session)

        new_id = TransactionsService().add_transaction(data)

        assert new_id is not None
        with Session(test_engine) as session:
            transaccion = session.get(Transaccion, new_id)
            assert transaccion.numero_socio == data["numero_socio"]
            assert transaccion.tipo == "pago"
            assert transaccion.monto == decimal.Decimal("45.00")
            assert transaccion.referencia == "Pago cuota enero"

    def test_id_socio_log_is_not_persisted_on_transaccion(self, test_engine):
        with Session(test_engine) as session:
            data = self._base_data(session)

        new_id = TransactionsService().add_transaction(data)

        with Session(test_engine) as session:
            transaccion = session.get(Transaccion, new_id)
            assert not hasattr(transaccion, "id_socio_log")

    def test_creates_audit_log_attributed_to_the_individual_socio(self, test_engine):
        with Session(test_engine) as session:
            data = self._base_data(session)
            expected_id_socio = data["id_socio_log"]

        new_id = TransactionsService().add_transaction(data)

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(tabla_afectada="transacciones").all()
            assert len(logs) == 1
            assert logs[0].id_registro_afectado == new_id
            assert logs[0].id_socio == expected_id_socio
            assert logs[0].accion == "crear"


class TestDuplicateTransactionRejection:
    def _base_data(self, session) -> dict:
        socio = _make_socio(session)
        metodo = _make_metodo(session)
        periodo = _make_periodo(session)
        session.commit()
        return {
            "numero_socio": socio.numero_socio,
            "id_socio_log": socio.id_socio,
            "id_periodo": periodo.id_periodo,
            "id_metodo": metodo.id_metodo,
            "tipo": "cargo",
            "monto": decimal.Decimal("45.00"),
            "fecha": datetime.date(2026, 1, 5),
            "referencia": None,
        }

    def test_rejects_exact_duplicate(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            data = self._base_data(session)

        first_id = service.add_transaction(data)
        second_id = service.add_transaction(data)

        assert first_id is not None
        assert second_id is None
        with Session(test_engine) as session:
            assert session.query(Transaccion).count() == 1

    def test_allows_same_socio_different_fecha(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            data = self._base_data(session)

        first_id = service.add_transaction(data)
        data2 = dict(data)
        data2["fecha"] = datetime.date(2026, 1, 6)
        second_id = service.add_transaction(data2)

        assert first_id is not None
        assert second_id is not None
        with Session(test_engine) as session:
            assert session.query(Transaccion).count() == 2

    def test_validate_transaction_reports_duplicate_without_persisting(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            data = self._base_data(session)

        service.add_transaction(data)
        error = service.validate_transaction(data)

        assert error is not None
        assert "idéntica" in error
        with Session(test_engine) as session:
            assert session.query(Transaccion).count() == 1


class TestRefundRequiresPriorPayment:
    def _setup_pago(self, session, monto: str = "45.00") -> dict:
        socio = _make_socio(session)
        metodo = _make_metodo(session)
        periodo = _make_periodo(session)
        session.commit()
        return {
            "numero_socio": socio.numero_socio,
            "id_socio_log": socio.id_socio,
            "id_periodo": periodo.id_periodo,
            "id_metodo": metodo.id_metodo,
            "tipo": "pago",
            "monto": decimal.Decimal(monto),
            "fecha": datetime.date(2026, 1, 5),
            "referencia": None,
        }

    def test_rejects_refund_with_no_prior_payment(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.commit()
            reembolso = {
                "numero_socio": socio.numero_socio,
                "id_socio_log": socio.id_socio,
                "id_periodo": periodo.id_periodo,
                "id_metodo": metodo.id_metodo,
                "tipo": "reembolso",
                "monto": decimal.Decimal("10.00"),
                "fecha": datetime.date(2026, 1, 6),
                "referencia": None,
            }

        new_id = service.add_transaction(reembolso)

        assert new_id is None
        with Session(test_engine) as session:
            assert session.query(Transaccion).count() == 0

    def test_allows_refund_covered_by_prior_payment(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            pago = self._setup_pago(session, "45.00")
        service.add_transaction(pago)

        reembolso = dict(pago, tipo="reembolso", monto=decimal.Decimal("20.00"), fecha=datetime.date(2026, 1, 10))
        new_id = service.add_transaction(reembolso)

        assert new_id is not None
        with Session(test_engine) as session:
            assert session.query(Transaccion).filter_by(tipo="reembolso").count() == 1

    def test_rejects_refund_exceeding_prior_payment(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            pago = self._setup_pago(session, "45.00")
        service.add_transaction(pago)

        reembolso = dict(pago, tipo="reembolso", monto=decimal.Decimal("50.00"), fecha=datetime.date(2026, 1, 10))
        new_id = service.add_transaction(reembolso)

        assert new_id is None
        with Session(test_engine) as session:
            assert session.query(Transaccion).filter_by(tipo="reembolso").count() == 0

    def test_rejects_refund_exceeding_pago_minus_prior_reembolso(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            pago = self._setup_pago(session, "45.00")
        service.add_transaction(pago)
        primer_reembolso = dict(pago, tipo="reembolso", monto=decimal.Decimal("30.00"), fecha=datetime.date(2026, 1, 10))
        assert service.add_transaction(primer_reembolso) is not None

        segundo_reembolso = dict(pago, tipo="reembolso", monto=decimal.Decimal("20.00"), fecha=datetime.date(2026, 1, 11))
        new_id = service.add_transaction(segundo_reembolso)

        assert new_id is None
        with Session(test_engine) as session:
            assert session.query(Transaccion).filter_by(tipo="reembolso").count() == 1

    def test_scoped_to_periodo_payment_in_other_periodo_does_not_count(self, test_engine):
        service = TransactionsService()
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo_enero = _make_periodo(session, nombre="Enero", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
            periodo_febrero = _make_periodo(session, nombre="Febrero", fecha_inicio=datetime.date(2026, 2, 1), fecha_fin=datetime.date(2026, 2, 28))
            session.commit()
            pago_enero = {
                "numero_socio": socio.numero_socio,
                "id_socio_log": socio.id_socio,
                "id_periodo": periodo_enero.id_periodo,
                "id_metodo": metodo.id_metodo,
                "tipo": "pago",
                "monto": decimal.Decimal("45.00"),
                "fecha": datetime.date(2026, 1, 5),
                "referencia": None,
            }
            reembolso_febrero = dict(pago_enero, id_periodo=periodo_febrero.id_periodo, tipo="reembolso", monto=decimal.Decimal("10.00"), fecha=datetime.date(2026, 2, 5))

        service.add_transaction(pago_enero)
        new_id = service.add_transaction(reembolso_febrero)

        assert new_id is None
        with Session(test_engine) as session:
            assert session.query(Transaccion).filter_by(tipo="reembolso").count() == 0


class TestListTransactions:
    def test_no_model_returns_zero(self, test_engine):
        assert TransactionsService().list_transactions("") == 0

    def test_does_not_duplicate_rows_for_a_shared_numero_socio(self, test_engine):
        """numero_socio is a shared family identifier - a naive join against
        Socio for display names would return one row per family member
        sharing it. A single Transaccion must still surface as one row.
        """
        with Session(test_engine) as session:
            _make_socio(session, numero_socio="1001", nombre="Marta", apellidos="Fernandez")
            _make_socio(session, numero_socio="1001", nombre="Jorge", apellidos="Fernandez")
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.add(
                Transaccion(
                    numero_socio="1001",
                    id_periodo=periodo.id_periodo,
                    id_metodo=metodo.id_metodo,
                    tipo="pago",
                    monto=decimal.Decimal("45.00"),
                    fecha=datetime.date(2026, 1, 5),
                )
            )
            session.commit()

        model = _FakeModel()
        added = TransactionsService().list_transactions("", model=model)

        assert added == 1
        assert len(model.rows) == 1

    def test_filters_by_tipo(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.add_all(
                [
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("45.00"), fecha=datetime.date(2026, 1, 5)),
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo.id_periodo, id_metodo=metodo.id_metodo, tipo="cargo", monto=decimal.Decimal("45.00"), fecha=datetime.date(2026, 1, 1)),
                ]
            )
            session.commit()

        model = _FakeModel()
        added = TransactionsService().list_transactions("", tipo="cargo", model=model)

        assert added == 1
        assert model.rows[0][3] == "cargo"

    def test_filters_by_periodo(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo_a = _make_periodo(session, nombre="Enero", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
            periodo_b = _make_periodo(session, nombre="Febrero", fecha_inicio=datetime.date(2026, 2, 1), fecha_fin=datetime.date(2026, 2, 28))
            session.add_all(
                [
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo_a.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("45.00"), fecha=datetime.date(2026, 1, 5)),
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo_b.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("45.00"), fecha=datetime.date(2026, 2, 5)),
                ]
            )
            session.commit()
            target_periodo_id = periodo_b.id_periodo

        model = _FakeModel()
        added = TransactionsService().list_transactions("", id_periodo=target_periodo_id, model=model)

        assert added == 1
        assert model.rows[0][6] == "Febrero"

    def test_search_matches_numero_socio_and_nombre(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session, numero_socio="1002", nombre="Jorge", apellidos="Dominguez")
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.add(
                Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("45.00"), fecha=datetime.date(2026, 1, 5))
            )
            session.commit()

        model = _FakeModel()
        added = TransactionsService().list_transactions("jorge", model=model)

        assert added == 1
        assert "Jorge" in model.rows[0][2]

    def test_orders_most_recent_fecha_first(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.add_all(
                [
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("10.00"), fecha=datetime.date(2026, 1, 1)),
                    Transaccion(numero_socio=socio.numero_socio, id_periodo=periodo.id_periodo, id_metodo=metodo.id_metodo, tipo="pago", monto=decimal.Decimal("20.00"), fecha=datetime.date(2026, 1, 20)),
                ]
            )
            session.commit()

        model = _FakeModel()
        TransactionsService().list_transactions("", model=model)

        assert [r[1] for r in model.rows] == ["2026-01-20", "2026-01-01"]
