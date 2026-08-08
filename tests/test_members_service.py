"""Tests for MembersService.add_member (toolbar_service.py).

add_member is the one write path in the members feature that already
persists (per CLAUDE.md's toolbar_service.py notes) - it uses
database.session.get_session(), which the test_engine fixture points at an
isolated per-test SQLite DB instead of data/club_manager.db.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from database.models import Socio
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
