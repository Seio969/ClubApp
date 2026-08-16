"""Tests for BalancesService (PLAN.md 2.5).

Covers the saldo_actual formula, the saldo_anterior chain across períodos,
cascading a recalculation forward into later períodos, and that
TransactionsService.add_transaction triggers it automatically.
"""

from __future__ import annotations

import datetime
import decimal

from sqlalchemy.orm import Session

from database.models import MetodoPago, Periodo, SaldoSocios, Socio, Transaccion
from features.balances.service import BalancesService
from features.transactions.service import TransactionsService


def _make_socio(session, **overrides) -> Socio:
    data = dict(numero_socio="1001", nombre="Marta", apellidos="Fernandez", estado="activo")
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


def _make_transaccion(session, socio, metodo, periodo, tipo, monto, fecha) -> Transaccion:
    t = Transaccion(
        numero_socio=socio.numero_socio,
        id_periodo=periodo.id_periodo,
        id_metodo=metodo.id_metodo,
        tipo=tipo,
        monto=decimal.Decimal(monto),
        fecha=fecha,
    )
    session.add(t)
    session.flush()
    return t


class TestRecalcularSaldo:
    def test_computes_saldo_actual_from_all_four_tipos(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            _make_transaccion(session, socio, metodo, periodo, "Cargo", "50.00", datetime.date(2026, 1, 1))
            _make_transaccion(session, socio, metodo, periodo, "Pago", "20.00", datetime.date(2026, 1, 5))
            _make_transaccion(session, socio, metodo, periodo, "Reembolso", "5.00", datetime.date(2026, 1, 6))
            _make_transaccion(session, socio, metodo, periodo, "Devolución", "10.00", datetime.date(2026, 1, 10))
            session.commit()

            periodo_id = periodo.id_periodo
            BalancesService().recalcular_saldo(session, socio.numero_socio, periodo_id)
            session.commit()

        with Session(test_engine) as session:
            saldo = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=periodo_id).first()
            assert saldo is not None
            assert saldo.cargos == decimal.Decimal("50.00")
            assert saldo.pagos == decimal.Decimal("20.00")
            assert saldo.reembolsos == decimal.Decimal("5.00")
            assert saldo.devoluciones == decimal.Decimal("10.00")
            assert saldo.saldo_anterior == decimal.Decimal("0")
            # 0 + 50 - 20 + 5 + 10
            assert saldo.saldo_actual == decimal.Decimal("45.00")

    def test_chains_saldo_anterior_from_previous_periodo(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            enero = _make_periodo(session, nombre="Enero", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
            febrero = _make_periodo(session, nombre="Febrero", fecha_inicio=datetime.date(2026, 2, 1), fecha_fin=datetime.date(2026, 2, 28))
            _make_transaccion(session, socio, metodo, enero, "Cargo", "40.00", datetime.date(2026, 1, 1))
            _make_transaccion(session, socio, metodo, febrero, "Cargo", "40.00", datetime.date(2026, 2, 1))
            session.commit()

            service = BalancesService()
            febrero_id = febrero.id_periodo
            service.recalcular_saldo(session, socio.numero_socio, enero.id_periodo)
            service.recalcular_saldo(session, socio.numero_socio, febrero_id)
            session.commit()

        with Session(test_engine) as session:
            saldo_febrero = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=febrero_id).first()
            assert saldo_febrero.saldo_anterior == decimal.Decimal("40.00")
            assert saldo_febrero.saldo_actual == decimal.Decimal("80.00")

    def test_cascades_forward_into_existing_later_periodo(self, test_engine):
        """Registering a transaction against an already-closed/past período
        must update every later período's chained saldo_anterior too, not
        just the período the transaction targets.
        """
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            enero = _make_periodo(session, nombre="Enero", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
            febrero = _make_periodo(session, nombre="Febrero", fecha_inicio=datetime.date(2026, 2, 1), fecha_fin=datetime.date(2026, 2, 28))
            _make_transaccion(session, socio, metodo, febrero, "Cargo", "40.00", datetime.date(2026, 2, 1))
            session.commit()

            service = BalancesService()
            febrero_id = febrero.id_periodo
            enero_id = enero.id_periodo
            # Establish febrero's row first (no enero row/transactions yet).
            service.recalcular_saldo(session, socio.numero_socio, febrero_id)
            session.commit()
            assert (
                session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=febrero_id).first().saldo_anterior
                == decimal.Decimal("0")
            )

            # A late-registered enero cargo should cascade into febrero.
            _make_transaccion(session, socio, metodo, enero, "Cargo", "40.00", datetime.date(2026, 1, 1))
            session.commit()
            service.recalcular_saldo(session, socio.numero_socio, enero_id)
            session.commit()

        with Session(test_engine) as session:
            saldo_febrero = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=febrero_id).first()
            assert saldo_febrero.saldo_anterior == decimal.Decimal("40.00")
            assert saldo_febrero.saldo_actual == decimal.Decimal("80.00")

    def test_recalculation_is_idempotent_and_upserts(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            _make_transaccion(session, socio, metodo, periodo, "Pago", "30.00", datetime.date(2026, 1, 5))
            session.commit()

            service = BalancesService()
            periodo_id = periodo.id_periodo
            service.recalcular_saldo(session, socio.numero_socio, periodo_id)
            service.recalcular_saldo(session, socio.numero_socio, periodo_id)
            session.commit()

        with Session(test_engine) as session:
            saldos = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=periodo_id).all()
            assert len(saldos) == 1
            assert saldos[0].saldo_actual == decimal.Decimal("-30.00")

    def test_noop_on_missing_numero_socio_or_periodo(self, test_engine):
        with Session(test_engine) as session:
            BalancesService().recalcular_saldo(session, None, 1)
            BalancesService().recalcular_saldo(session, "1001", None)
            BalancesService().recalcular_saldo(session, "1001", 9999)
            session.commit()
            assert session.query(SaldoSocios).count() == 0


class TestAddTransactionTriggersRecalculation:
    def test_add_transaction_creates_saldo_row(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.commit()
            data = {
                "numero_socio": socio.numero_socio,
                "id_socio_log": socio.id_socio,
                "id_periodo": periodo.id_periodo,
                "id_metodo": metodo.id_metodo,
                "tipo": "Cargo",
                "monto": decimal.Decimal("42.00"),
                "fecha": datetime.date(2026, 1, 5),
                "referencia": None,
            }

        new_id = TransactionsService().add_transaction(data)

        assert new_id is not None
        with Session(test_engine) as session:
            saldo = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=periodo.id_periodo).first()
            assert saldo is not None
            assert saldo.cargos == decimal.Decimal("42.00")
            assert saldo.saldo_actual == decimal.Decimal("42.00")

    def test_second_transaction_updates_existing_saldo_row(self, test_engine):
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.commit()
            base = {
                "numero_socio": socio.numero_socio,
                "id_socio_log": socio.id_socio,
                "id_periodo": periodo.id_periodo,
                "id_metodo": metodo.id_metodo,
                "monto": decimal.Decimal("42.00"),
                "referencia": None,
            }

        service = TransactionsService()
        service.add_transaction(dict(base, tipo="Cargo", fecha=datetime.date(2026, 1, 1)))
        service.add_transaction(dict(base, tipo="Pago", monto=decimal.Decimal("42.00"), fecha=datetime.date(2026, 1, 5)))

        with Session(test_engine) as session:
            saldos = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=periodo.id_periodo).all()
            assert len(saldos) == 1
            assert saldos[0].saldo_actual == decimal.Decimal("0.00")

    def test_rejected_transaction_does_not_recalculate(self, test_engine):
        """A duplicate/rejected add_transaction call must not touch
        SaldoSocios - the recalculation call sits inside the same
        validated write path, not before it.
        """
        with Session(test_engine) as session:
            socio = _make_socio(session)
            metodo = _make_metodo(session)
            periodo = _make_periodo(session)
            session.commit()
            data = {
                "numero_socio": socio.numero_socio,
                "id_socio_log": socio.id_socio,
                "id_periodo": periodo.id_periodo,
                "id_metodo": metodo.id_metodo,
                "tipo": "Cargo",
                "monto": decimal.Decimal("42.00"),
                "fecha": datetime.date(2026, 1, 5),
                "referencia": None,
            }

        service = TransactionsService()
        service.add_transaction(data)
        rejected_id = service.add_transaction(data)

        assert rejected_id is None
        with Session(test_engine) as session:
            saldo = session.query(SaldoSocios).filter_by(numero_socio="1001", id_periodo=periodo.id_periodo).first()
            assert saldo.cargos == decimal.Decimal("42.00")
