"""Tests for database.seed_db - fixed metodos_pago seeding (PLAN.md 2.7 / 3.5)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import MetodoPago
from database.seed_db import METODOS_PAGO_FIJOS, seed_metodos_pago


class TestSeedMetodosPago:
    def test_inserts_all_fixed_methods_on_empty_table(self, test_engine):
        inserted = seed_metodos_pago()

        assert inserted == len(METODOS_PAGO_FIJOS)
        with Session(test_engine) as session:
            nombres = {row.nombre for row in session.query(MetodoPago).all()}
            assert nombres == set(METODOS_PAGO_FIJOS)

    def test_is_idempotent_on_second_call(self, test_engine):
        seed_metodos_pago()

        inserted_again = seed_metodos_pago()

        assert inserted_again == 0
        with Session(test_engine) as session:
            assert session.query(MetodoPago).count() == len(METODOS_PAGO_FIJOS)

    def test_only_inserts_missing_methods(self, test_engine):
        with Session(test_engine) as session:
            session.add(MetodoPago(nombre="EFECTIVO"))
            session.commit()

        inserted = seed_metodos_pago()

        assert inserted == len(METODOS_PAGO_FIJOS) - 1
        with Session(test_engine) as session:
            nombres = {row.nombre for row in session.query(MetodoPago).all()}
            assert nombres == set(METODOS_PAGO_FIJOS)

    def test_preserves_custom_methods_not_in_fixed_list(self, test_engine):
        with Session(test_engine) as session:
            session.add(MetodoPago(nombre="BIZUM"))
            session.commit()

        seed_metodos_pago()

        with Session(test_engine) as session:
            nombres = {row.nombre for row in session.query(MetodoPago).all()}
            assert "BIZUM" in nombres
            assert nombres == set(METODOS_PAGO_FIJOS) | {"BIZUM"}
