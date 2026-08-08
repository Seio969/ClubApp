"""Tests for common.view_registry.ViewRegistry.

view_registry imports `engine` by name at module load time, so it holds a
reference the test_engine fixture patches separately from
database.session.engine (see conftest.py) - constructing ViewRegistry()
inside a test (after the fixture has run) picks up the patched engine.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from common.view_registry import ViewRegistry
from database.models import Socio

EXPECTED_TABLES = {
    "socios",
    "metodos_pago",
    "periodo",
    "reglas_cobro",
    "transacciones",
    "saldos_socios",
    "logs",
}


def _insert_socios(engine, count: int) -> None:
    with Session(engine) as session:
        for i in range(count):
            session.add(
                Socio(
                    numero_socio=f"100{i}",
                    nombre=f"Nombre{i}",
                    apellidos=f"Apellidos{i}",
                    estado="activo",
                )
            )
        session.commit()


class TestViewRegistryInit:
    def test_auto_registers_every_db_table(self, test_engine):
        registry = ViewRegistry()

        assert EXPECTED_TABLES <= set(registry.get_views())


class TestFetchTable:
    def test_returns_columns_and_rows(self, test_engine):
        _insert_socios(test_engine, 2)
        registry = ViewRegistry()

        keys, rows = registry.fetch_table("socios")

        assert "nombre" in keys
        assert len(rows) == 2

    def test_limit_restricts_row_count(self, test_engine):
        _insert_socios(test_engine, 3)
        registry = ViewRegistry()

        _, rows = registry.fetch_table("socios", limit=1)

        assert len(rows) == 1

    def test_limit_zero_means_no_limit(self, test_engine):
        _insert_socios(test_engine, 3)
        registry = ViewRegistry()

        _, rows = registry.fetch_table("socios", limit=0)

        assert len(rows) == 3

    def test_unknown_table_returns_empty(self, test_engine):
        registry = ViewRegistry()

        keys, rows = registry.fetch_table("no_such_table")

        assert keys == []
        assert rows == []


class TestFetchView:
    def test_table_type_dispatches_to_fetch_table(self, test_engine):
        _insert_socios(test_engine, 1)
        registry = ViewRegistry()

        keys, rows = registry.fetch_view("socios")

        assert "nombre" in keys
        assert len(rows) == 1

    def test_sql_view_returns_query_results(self, test_engine):
        _insert_socios(test_engine, 2)
        registry = ViewRegistry()
        registry.register_sql_view("solo_nombres", "SELECT nombre FROM socios")

        keys, rows = registry.fetch_view("solo_nombres")

        assert keys == ["nombre"]
        assert len(rows) == 2

    def test_sql_view_respects_limit(self, test_engine):
        _insert_socios(test_engine, 3)
        registry = ViewRegistry()
        registry.register_sql_view("solo_nombres", "SELECT nombre FROM socios")

        _, rows = registry.fetch_view("solo_nombres", limit=1)

        assert len(rows) == 1

    def test_callable_view_returns_func_result(self, test_engine):
        registry = ViewRegistry()
        registry.register_callable_view("custom", lambda: (["a", "b"], [(1, 2), (3, 4)]))

        keys, rows = registry.fetch_view("custom")

        assert keys == ["a", "b"]
        assert rows == [(1, 2), (3, 4)]

    def test_callable_view_respects_limit(self, test_engine):
        registry = ViewRegistry()
        registry.register_callable_view("custom", lambda: (["a"], [(1,), (2,), (3,)]))

        _, rows = registry.fetch_view("custom", limit=2)

        assert rows == [(1,), (2,)]

    def test_unknown_view_returns_empty(self, test_engine):
        registry = ViewRegistry()

        keys, rows = registry.fetch_view("does_not_exist")

        assert keys == []
        assert rows == []
