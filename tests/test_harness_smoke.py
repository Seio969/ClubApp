"""Smoke test for the test harness itself: pytest runs, `src/` imports
resolve, and the `test_engine` fixture produces an isolated DB rather than
touching the real `data/club_manager.db`.
"""

from __future__ import annotations

from pathlib import Path

from database.session import engine as configured_engine
from database.models import Socio


def test_test_engine_is_isolated_from_real_db(test_engine):
    assert test_engine is not configured_engine

    real_db_path = Path(str(configured_engine.url.database))
    test_db_path = Path(str(test_engine.url.database))
    assert test_db_path != real_db_path
    assert not real_db_path.exists() or test_db_path.parent != real_db_path.parent


def test_test_engine_has_expected_tables(test_engine):
    from sqlalchemy import inspect as sqlalchemy_inspect

    tables = set(sqlalchemy_inspect(test_engine).get_table_names())
    assert {"socios", "metodos_pago", "periodo", "transacciones", "saldos_socios", "logs"} <= tables


def test_test_engine_starts_empty(test_engine):
    from sqlalchemy.orm import Session

    with Session(test_engine) as session:
        assert session.query(Socio).count() == 0
