"""Tests for database.seed_db - fixed metodos_pago and reglas_cobro seeding (PLAN.md 2.7 / 3.5)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import MetodoPago, ReglaCobro
from database.seed_db import (
    METODOS_PAGO_FIJOS,
    REGLAS_COBRO_INICIALES,
    seed_metodos_pago,
    seed_reglas_cobro,
)


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


class TestSeedReglasCobro:
    def test_inserts_all_initial_rules_on_empty_table(self, test_engine):
        inserted = seed_reglas_cobro()

        assert inserted == len(REGLAS_COBRO_INICIALES)
        with Session(test_engine) as session:
            descripciones = {row.descripcion for row in session.query(ReglaCobro).all()}
            assert descripciones == {r["descripcion"] for r in REGLAS_COBRO_INICIALES}

    def test_is_idempotent_on_second_call(self, test_engine):
        seed_reglas_cobro()

        inserted_again = seed_reglas_cobro()

        assert inserted_again == 0
        with Session(test_engine) as session:
            assert session.query(ReglaCobro).count() == len(REGLAS_COBRO_INICIALES)

    def test_only_inserts_missing_rules(self, test_engine):
        with Session(test_engine) as session:
            session.add(ReglaCobro(descripcion="Cuota mensual estándar", cuota_mensual=36.00))
            session.commit()

        inserted = seed_reglas_cobro()

        assert inserted == 0
        with Session(test_engine) as session:
            assert session.query(ReglaCobro).count() == 1

    def test_preserves_custom_rules_not_in_initial_list(self, test_engine):
        with Session(test_engine) as session:
            session.add(ReglaCobro(descripcion="Cuota reducida", cuota_mensual=18.00))
            session.commit()

        seed_reglas_cobro()

        with Session(test_engine) as session:
            descripciones = {row.descripcion for row in session.query(ReglaCobro).all()}
            expected = {r["descripcion"] for r in REGLAS_COBRO_INICIALES} | {"Cuota reducida"}
            assert descripciones == expected
