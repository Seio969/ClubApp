"""Tests for ResetService (PLAN.md 2.15): full and scoped database resets.

full_reset() drops and recreates every table then re-seeds metodos_pago;
scoped_reset() only clears transacciones/saldos_socios/periodo, leaving
socios/metodos_pago/reglas_cobro/logs untouched. Both record a Log row
documenting the reset itself (full_reset's lands in the freshly recreated
logs table, since the wipe removes everything that came before it).
"""

from __future__ import annotations

import datetime
import decimal

from sqlalchemy.orm import Session

from database.models import Log, MetodoPago, Periodo, ReglaCobro, SaldoSocios, Socio, Transaccion
from database.seed_db import METODOS_PAGO_FIJOS, seed_metodos_pago
from features.settings.reset_service import ResetService


def _seed_full_dataset(test_engine) -> dict:
    """Populate every table with at least one row, return the ids used."""
    seed_metodos_pago()
    with Session(test_engine) as session:
        socio = Socio(numero_socio="1001", nombre="Marta", apellidos="Fernandez")
        session.add(socio)
        session.flush()

        periodo = Periodo(nombre="Enero 2026", fecha_inicio=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2026, 1, 31))
        session.add(periodo)
        session.flush()

        metodo = session.query(MetodoPago).filter_by(nombre="EFECTIVO").one()

        transaccion = Transaccion(
            numero_socio="1001",
            id_periodo=periodo.id_periodo,
            id_metodo=metodo.id_metodo,
            tipo="pago",
            monto=decimal.Decimal("45.00"),
        )
        session.add(transaccion)

        saldo = SaldoSocios(numero_socio="1001", id_periodo=periodo.id_periodo, saldo_actual=decimal.Decimal("0.00"))
        session.add(saldo)

        regla = ReglaCobro(descripcion="Cuota general", cuota_mensual=decimal.Decimal("45.00"), estado="activo")
        session.add(regla)

        session.commit()
        return {
            "id_socio": socio.id_socio,
            "id_periodo": periodo.id_periodo,
            "id_regla": regla.id_regla,
        }


class TestFullReset:
    def test_wipes_every_table_and_reseeds_metodos_pago(self, test_engine):
        _seed_full_dataset(test_engine)
        service = ResetService()

        ok = service.full_reset()

        assert ok is True
        with Session(test_engine) as session:
            assert session.query(Socio).count() == 0
            assert session.query(Transaccion).count() == 0
            assert session.query(SaldoSocios).count() == 0
            assert session.query(Periodo).count() == 0
            assert session.query(ReglaCobro).count() == 0
            nombres = {row.nombre for row in session.query(MetodoPago).all()}
            assert nombres == set(METODOS_PAGO_FIJOS)

    def test_records_a_log_row_in_the_fresh_database(self, test_engine):
        _seed_full_dataset(test_engine)
        service = ResetService()

        service.full_reset()

        with Session(test_engine) as session:
            logs = session.query(Log).all()
            assert len(logs) == 1
            assert logs[0].accion == "reset_completo"
            assert logs[0].id_socio is None


class TestScopedReset:
    def test_clears_only_transacciones_saldos_and_periodos(self, test_engine):
        ids = _seed_full_dataset(test_engine)
        service = ResetService()

        ok = service.scoped_reset()

        assert ok is True
        with Session(test_engine) as session:
            assert session.query(Transaccion).count() == 0
            assert session.query(SaldoSocios).count() == 0
            assert session.query(Periodo).count() == 0
            # kept
            assert session.get(Socio, ids["id_socio"]) is not None
            assert session.get(ReglaCobro, ids["id_regla"]) is not None
            nombres = {row.nombre for row in session.query(MetodoPago).all()}
            assert nombres == set(METODOS_PAGO_FIJOS)

    def test_preserves_existing_log_history(self, test_engine):
        ids = _seed_full_dataset(test_engine)
        with Session(test_engine) as session:
            session.add(Log(id_socio=ids["id_socio"], accion="crear", tabla_afectada="socios", descripcion_cambio="test"))
            session.commit()
        service = ResetService()

        service.scoped_reset()

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="crear").all()
            assert len(logs) == 1

    def test_records_a_log_row_for_the_reset_itself(self, test_engine):
        _seed_full_dataset(test_engine)
        service = ResetService()

        service.scoped_reset()

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="reset_parcial").all()
            assert len(logs) == 1
            assert logs[0].id_socio is None
