"""Tests for ReglasCobroService's billing-rules CRUD (PLAN.md 2.7).

Unlike MetodoPago, there's no fixed set here - every rule is fully
editable. Nothing is ever physically deleted: "remove" is always
estado="inactivo", same pattern as Socio/MetodoPago. Each write records
a Log row via database.audit.record_log.
"""

from __future__ import annotations

import decimal

from sqlalchemy.orm import Session

from database.models import Log, ReglaCobro
from features.settings.reglas_cobro_service import ReglasCobroService


def _valid_regla_data(**overrides) -> dict:
    data = dict(
        descripcion="Cuota general",
        cuota_mensual=decimal.Decimal("45.00"),
        plazo_pago=30,
        penalizacion=decimal.Decimal("5.00"),
        descuento=decimal.Decimal("0.00"),
    )
    data.update(overrides)
    return data


class TestAddReglaCobro:
    def test_persists_and_returns_new_id(self, test_engine):
        service = ReglasCobroService()

        new_id = service.add_regla_cobro(_valid_regla_data())

        assert new_id is not None
        with Session(test_engine) as session:
            regla = session.get(ReglaCobro, new_id)
            assert regla.descripcion == "Cuota general"
            assert regla.cuota_mensual == decimal.Decimal("45.00")
            assert regla.plazo_pago == 30
            assert regla.estado == "activo"

    def test_allows_multiple_named_rules(self, test_engine):
        service = ReglasCobroService()

        id_a = service.add_regla_cobro(_valid_regla_data(descripcion="Cuota general"))
        id_b = service.add_regla_cobro(_valid_regla_data(descripcion="Cuota reducida", cuota_mensual=decimal.Decimal("25.00")))

        assert id_a is not None and id_b is not None and id_a != id_b
        with Session(test_engine) as session:
            assert session.query(ReglaCobro).count() == 2

    def test_creates_audit_log_row(self, test_engine):
        service = ReglasCobroService()

        new_id = service.add_regla_cobro(_valid_regla_data())

        with Session(test_engine) as session:
            logs = session.query(Log).all()
            assert len(logs) == 1
            assert logs[0].accion == "crear"
            assert logs[0].tabla_afectada == "reglas_cobro"
            assert logs[0].id_registro_afectado == new_id
            assert logs[0].id_socio is None


class TestGetReglaCobro:
    def test_returns_editable_fields(self, test_engine):
        service = ReglasCobroService()
        new_id = service.add_regla_cobro(_valid_regla_data())

        data = service.get_regla_cobro(new_id)

        assert data == _valid_regla_data()

    def test_returns_none_for_unknown_id(self, test_engine):
        service = ReglasCobroService()

        assert service.get_regla_cobro(999) is None


class TestUpdateReglaCobro:
    def test_persists_changes(self, test_engine):
        service = ReglasCobroService()
        new_id = service.add_regla_cobro(_valid_regla_data())

        ok = service.update_regla_cobro(new_id, _valid_regla_data(cuota_mensual=decimal.Decimal("50.00")))

        assert ok is True
        with Session(test_engine) as session:
            assert session.get(ReglaCobro, new_id).cuota_mensual == decimal.Decimal("50.00")

    def test_returns_false_for_unknown_id(self, test_engine):
        service = ReglasCobroService()

        assert service.update_regla_cobro(999, _valid_regla_data()) is False

    def test_creates_audit_log_row_describing_changed_fields(self, test_engine):
        service = ReglasCobroService()
        new_id = service.add_regla_cobro(_valid_regla_data())

        service.update_regla_cobro(new_id, _valid_regla_data(cuota_mensual=decimal.Decimal("50.00")))

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="editar").all()
            assert len(logs) == 1
            assert "cuota_mensual" in logs[0].descripcion_cambio


class TestSetReglaCobroEstado:
    def test_deactivates_and_reactivates(self, test_engine):
        service = ReglasCobroService()
        new_id = service.add_regla_cobro(_valid_regla_data())

        assert service.set_regla_cobro_estado(new_id, "inactivo") is True
        with Session(test_engine) as session:
            assert session.get(ReglaCobro, new_id).estado == "inactivo"

        assert service.set_regla_cobro_estado(new_id, "activo") is True
        with Session(test_engine) as session:
            assert session.get(ReglaCobro, new_id).estado == "activo"

    def test_creates_audit_log_row(self, test_engine):
        service = ReglasCobroService()
        new_id = service.add_regla_cobro(_valid_regla_data())

        service.set_regla_cobro_estado(new_id, "inactivo")

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="desactivar").all()
            assert len(logs) == 1
            assert logs[0].id_registro_afectado == new_id

    def test_returns_false_for_unknown_id(self, test_engine):
        service = ReglasCobroService()

        assert service.set_regla_cobro_estado(999, "inactivo") is False


class TestListReglasCobro:
    def test_lists_all_rules_any_estado(self, test_engine):
        service = ReglasCobroService()
        id_a = service.add_regla_cobro(_valid_regla_data(descripcion="Cuota general"))
        id_b = service.add_regla_cobro(_valid_regla_data(descripcion="Cuota reducida"))
        service.set_regla_cobro_estado(id_b, "inactivo")

        rows = service.list_reglas_cobro()

        assert {r["id_regla"] for r in rows} == {id_a, id_b}
        estados = {r["id_regla"]: r["estado"] for r in rows}
        assert estados[id_a] == "activo"
        assert estados[id_b] == "inactivo"
