"""Shared pytest fixtures.

`pythonpath = ["src"]` in pyproject.toml puts `src/` on sys.path the same
way running the app via `src/main.py` does, so tests use the same absolute
imports as the app (`from database.models import Socio`, etc.).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base


@pytest.fixture()
def test_engine(tmp_path, monkeypatch):
    """Isolated, per-test SQLite database.

    Code under test (`database.session.get_session`, `ViewRegistry`, ...)
    talks to the DB through module-level `engine`/`SessionLocal` globals, so
    this fixture monkeypatches those globals to point at a throwaway
    file-based SQLite DB instead of the real `data/club_manager.db`. Each
    test gets its own file under pytest's `tmp_path`, so tests never see
    each other's data and never touch developer/production data.
    """
    db_path = tmp_path / "test_club.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    import database.session as session_module

    monkeypatch.setattr(session_module, "engine", engine)
    monkeypatch.setattr(session_module, "SessionLocal", session_factory)

    try:
        import common.view_registry as view_registry_module

        # view_registry imported `engine` by name, so it holds its own
        # reference that patching database.session.engine doesn't reach.
        monkeypatch.setattr(view_registry_module, "engine", engine)
    except ImportError:
        pass

    yield engine
    engine.dispose()
