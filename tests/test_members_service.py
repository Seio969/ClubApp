"""Tests for MembersService's write paths (toolbar_service.py):
add_member, get_member/update_member and delete_members.

All of these use database.session.get_session(), which the test_engine
fixture points at an isolated per-test SQLite DB instead of
data/club_manager.db. Each write path also records a Log row in the same
transaction (database.audit.record_log, PLAN.md 2.12) - covered here
alongside the write itself.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from database.models import Log, Socio
from features.members.toolbar_service import MembersService


def _valid_socio_data(**overrides) -> dict:
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
    return data


class TestAddMember:
    def test_persists_and_returns_new_id(self, test_engine):
        service = MembersService()

        new_id = service.add_member(_valid_socio_data())

        assert new_id is not None
        with Session(test_engine) as session:
            socio = session.get(Socio, new_id)
            assert socio is not None
            assert socio.numero_socio == "1001"
            assert socio.nombre == "Marta"
            assert socio.apellidos == "Fernandez Ruiz"
            assert socio.telefono == "612345678"
            assert socio.email == "marta@example.com"
            assert socio.estado == "activo"

    def test_returns_none_and_persists_nothing_on_constraint_violation(self, test_engine):
        service = MembersService()
        data = _valid_socio_data()
        del data["nombre"]  # Socio.nombre is NOT NULL

        new_id = service.add_member(data)

        assert new_id is None
        with Session(test_engine) as session:
            assert session.query(Socio).count() == 0

    def test_numero_socio_is_not_unique_across_members(self, test_engine):
        # numero_socio is an intentionally shared family/household identifier
        # (see the comment on Socio.numero_socio in models.py) - two members
        # must be able to share one without add_member rejecting the second.
        service = MembersService()

        id_a = service.add_member(_valid_socio_data(nombre="Marta"))
        id_b = service.add_member(_valid_socio_data(nombre="Jose"))

        assert id_a is not None
        assert id_b is not None
        assert id_a != id_b
        with Session(test_engine) as session:
            rows = session.query(Socio).filter_by(numero_socio="1001").all()
            assert {row.nombre for row in rows} == {"Marta", "Jose"}

    def test_creates_audit_log_row(self, test_engine):
        service = MembersService()

        new_id = service.add_member(_valid_socio_data())

        with Session(test_engine) as session:
            logs = session.query(Log).all()
            assert len(logs) == 1
            assert logs[0].id_socio == new_id
            assert logs[0].accion == "crear"
            assert logs[0].tabla_afectada == "socios"
            assert logs[0].id_registro_afectado == new_id
            assert "1001" in logs[0].descripcion_cambio

    def test_no_audit_log_on_constraint_violation(self, test_engine):
        service = MembersService()
        data = _valid_socio_data()
        del data["nombre"]

        service.add_member(data)

        with Session(test_engine) as session:
            assert session.query(Log).count() == 0


class TestGetMember:
    def test_returns_editable_fields_for_existing_member(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())

        data = service.get_member(new_id)

        assert data == _valid_socio_data()

    def test_returns_none_for_unknown_id(self, test_engine):
        service = MembersService()

        assert service.get_member(999) is None


class TestUpdateMember:
    def test_persists_changes(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())

        ok = service.update_member(new_id, _valid_socio_data(nombre="Marta Actualizada", telefono="600000000"))

        assert ok is True
        with Session(test_engine) as session:
            socio = session.get(Socio, new_id)
            assert socio.nombre == "Marta Actualizada"
            assert socio.telefono == "600000000"
            # Untouched fields from the same full-form submission stay as given
            assert socio.numero_socio == "1001"

    def test_returns_false_for_unknown_id(self, test_engine):
        service = MembersService()

        ok = service.update_member(999, _valid_socio_data())

        assert ok is False

    def test_returns_false_and_leaves_data_unchanged_on_constraint_violation(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())
        data = _valid_socio_data()
        data["nombre"] = None  # Socio.nombre is NOT NULL

        ok = service.update_member(new_id, data)

        assert ok is False
        with Session(test_engine) as session:
            socio = session.get(Socio, new_id)
            assert socio.nombre == "Marta"

    def test_creates_audit_log_row_describing_changed_fields(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())

        service.update_member(new_id, _valid_socio_data(nombre="Marta Actualizada", telefono="600000000"))

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="editar").all()
            assert len(logs) == 1
            log = logs[0]
            assert log.id_socio == new_id
            assert log.tabla_afectada == "socios"
            assert log.id_registro_afectado == new_id
            assert "nombre" in log.descripcion_cambio
            assert "Marta Actualizada" in log.descripcion_cambio
            assert "telefono" in log.descripcion_cambio
            # apellidos wasn't changed by this update - shouldn't appear as a diff
            assert "apellidos" not in log.descripcion_cambio

    def test_no_audit_log_for_unknown_id(self, test_engine):
        service = MembersService()

        service.update_member(999, _valid_socio_data())

        with Session(test_engine) as session:
            assert session.query(Log).count() == 0


class TestDeleteMembers:
    def test_deactivates_and_returns_row(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())

        def model_getter(row, col):
            return str(new_id)

        removed = service.delete_members([0], model_getter)

        assert removed == [0]
        with Session(test_engine) as session:
            socio = session.get(Socio, new_id)
            assert socio.estado == "inactivo"

    def test_creates_audit_log_row(self, test_engine):
        service = MembersService()
        new_id = service.add_member(_valid_socio_data())

        def model_getter(row, col):
            return str(new_id)

        service.delete_members([0], model_getter)

        with Session(test_engine) as session:
            logs = session.query(Log).filter_by(accion="desactivar").all()
            assert len(logs) == 1
            assert logs[0].id_socio == new_id
            assert logs[0].tabla_afectada == "socios"
            assert logs[0].id_registro_afectado == new_id
            assert "1001" in logs[0].descripcion_cambio

    def test_empty_selection_returns_empty_and_logs_nothing(self, test_engine):
        service = MembersService()

        removed = service.delete_members([], lambda row, col: "1")

        assert removed == []
        with Session(test_engine) as session:
            assert session.query(Log).count() == 0

    def test_no_model_getter_returns_empty(self, test_engine):
        service = MembersService()

        removed = service.delete_members([0], None)

        assert removed == []

    def test_unknown_id_socio_is_skipped_without_log(self, test_engine):
        service = MembersService()

        removed = service.delete_members([0], lambda row, col: "999")

        assert removed == []
        with Session(test_engine) as session:
            assert session.query(Log).count() == 0
