"""Tests for MetodosPagoService's metodos_pago CRUD (PLAN.md 2.7).

Fixed methods (the 5 from README.md, database.seed_db.METODOS_PAGO_FIJOS)
are protected from renaming; nothing is ever physically deleted - "remove"
is always estado="inactivo", the same pattern MembersService uses for
Socio. Each write records a Log row via database.audit.record_log, same
as MembersService.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import Log, MetodoPago
from database.seed_db import METODOS_PAGO_FIJOS, seed_metodos_pago
from features.settings.metodos_pago.service import MetodosPagoService


class TestListMetodosPago:
    def test_flags_fixed_vs_custom(self, test_engine):
        seed_metodos_pago()
        service = MetodosPagoService()
        service.add_metodo_pago("BIZUM")

        rows = service.list_metodos_pago()

        fixed_names = {r["nombre"] for r in rows if r["fijo"]}
        custom_names = {r["nombre"] for r in rows if not r["fijo"]}
        assert fixed_names == set(METODOS_PAGO_FIJOS)
        assert custom_names == {"BIZUM"}
        assert all(r["estado"] == "activo" for r in rows)


class TestAddMetodoPago:
    def test_persists_and_returns_new_id(self, test_engine):
        service = MetodosPagoService()

        new_id = service.add_metodo_pago("BIZUM")

        assert new_id is not None
        with Session(test_engine) as session:
            metodo = session.get(MetodoPago, new_id)
            assert metodo.nombre == "BIZUM"
            assert metodo.estado == "activo"

    def test_rejects_duplicate_name(self, test_engine):
        service = MetodosPagoService()
        service.add_metodo_pago("BIZUM")

        second_id = service.add_metodo_pago("BIZUM")

        assert second_id is None
        with Session(test_engine) as session:
            assert session.query(MetodoPago).filter_by(nombre="BIZUM").count() == 1

    def test_creates_audit_log_row(self, test_engine):
        service = MetodosPagoService()

        new_id = service.add_metodo_pago("BIZUM")

        with Session(test_engine) as session:
            logs = session.query(Log).all()
            assert len(logs) == 1
            assert logs[0].accion == "crear"
            assert logs[0].tabla_afectada == "metodos_pago"
            assert logs[0].id_registro_afectado == new_id
            assert logs[0].id_socio is None


class TestRenameMetodoPago:
    def test_renames_custom_method(self, test_engine):
        service = MetodosPagoService()
        new_id = service.add_metodo_pago("BIZUM")

        ok = service.rename_metodo_pago(new_id, "BIZUM 2")

        assert ok is True
        with Session(test_engine) as session:
            assert session.get(MetodoPago, new_id).nombre == "BIZUM 2"

    def test_refuses_to_rename_fixed_method(self, test_engine):
        seed_metodos_pago()
        service = MetodosPagoService()
        with Session(test_engine) as session:
            efectivo_id = session.query(MetodoPago).filter_by(nombre="EFECTIVO").one().id_metodo

        ok = service.rename_metodo_pago(efectivo_id, "CASH")

        assert ok is False
        with Session(test_engine) as session:
            assert session.get(MetodoPago, efectivo_id).nombre == "EFECTIVO"

    def test_returns_false_for_unknown_id(self, test_engine):
        service = MetodosPagoService()

        assert service.rename_metodo_pago(999, "BIZUM") is False


class TestSetMetodoPagoEstado:
    def test_deactivates_and_reactivates_custom_method(self, test_engine):
        service = MetodosPagoService()
        new_id = service.add_metodo_pago("BIZUM")

        assert service.set_metodo_pago_estado(new_id, "inactivo") is True
        with Session(test_engine) as session:
            assert session.get(MetodoPago, new_id).estado == "inactivo"

        assert service.set_metodo_pago_estado(new_id, "activo") is True
        with Session(test_engine) as session:
            assert session.get(MetodoPago, new_id).estado == "activo"

    def test_can_deactivate_a_fixed_method(self, test_engine):
        # Fixed methods can't be renamed/deleted, but can be deactivated -
        # e.g. the club stops accepting a method without erasing it.
        seed_metodos_pago()
        service = MetodosPagoService()
        with Session(test_engine) as session:
            efectivo_id = session.query(MetodoPago).filter_by(nombre="EFECTIVO").one().id_metodo

        ok = service.set_metodo_pago_estado(efectivo_id, "inactivo")

        assert ok is True
        with Session(test_engine) as session:
            metodo = session.get(MetodoPago, efectivo_id)
            assert metodo.estado == "inactivo"
            assert metodo.nombre == "EFECTIVO"

    def test_creates_audit_log_row(self, test_engine):
        service = MetodosPagoService()
        new_id = service.add_metodo_pago("BIZUM")

        service.set_metodo_pago_estado(new_id, "inactivo")

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="desactivar").all()
            assert len(logs) == 1
            assert logs[0].id_registro_afectado == new_id

    def test_returns_false_for_unknown_id(self, test_engine):
        service = MetodosPagoService()

        assert service.set_metodo_pago_estado(999, "inactivo") is False
