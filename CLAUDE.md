# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. It's deliberately kept lean — it's injected in full on every turn of every session. Full per-file/per-class architecture detail lives in [ARCHITECTURE.md](ARCHITECTURE.md); read the relevant section there on demand (via the Read tool) before touching a file you haven't touched yet this session, rather than assuming from this summary.

## Project overview

Desktop management app ("Club Social Paraiso") for a club's members and finances: member records, dues/payments/refunds, per-period balances, and reporting. Built with **PySide6** (Qt) for the UI, **SQLAlchemy** ORM over **SQLite** for persistence. Domain/UI text and identifiers are in Spanish (Socio = member, Transaccion = transaction, Periodo = period, etc.) — match this convention when adding new domain code.

The app is early-stage: the "Gestionar Miembros" (members) screen, a "🧾 Transacciones" screen, and a "⚙️ Ajustes" (settings) hub are wired up from the main menu. Within Members, member CRUD (search, create, edit, deactivate) is fully implemented and audit-logged; export remains a logging placeholder (see [architecture/members.md](architecture/members.md)) — transaction-registration ("Registrar") is real, opening the shared `TransactionDialog`. Within Ajustes, payment methods (`metodos_pago`) and billing rules (`reglas_cobro`) both have full CRUD, and a database reset action (full wipe + scoped reset) exists. Transactions (charges/pagos/reembolsos) have full CRUD-minus-edit (create + browse, no update/delete) with integrity validation, but balance calculation (`SaldoSocios`) and period management (`Periodo`) beyond a minimal quick-create are still unbuilt. Reports don't exist yet.

See [README.md](README.md) for the full functional/non-functional requirements spec (in Spanish), [db.md](db.md) for a mermaid ER diagram of the *intended* schema (note: it has drifted from the actual code — see "Schema drift" in [architecture/database.md](architecture/database.md)), and [PLAN.md](PLAN.md) for the current task backlog.

## Commands

Dependencies are managed with **uv** (`uv.lock` is present; no `requirements.txt`, no `pip`).

- Install deps: `uv sync`
- Run the app (from repo root): `uv run python src/main.py`
- Initialize/reset the DB schema only: `uv run python src/database/init_db.py` (calls `Base.metadata.create_all` — creates missing tables, does **not** drop/alter existing ones; a small stopgap in `init_db()` (`_add_missing_columns`) ALTERs in the specific columns known to have been added after tables already existed — see [architecture/database.md](architecture/database.md)'s `database/init_db.py` section — but any other schema change still needs the DB file deleted to fully rebuild). Also seeds the fixed `metodos_pago` rows via `database/seed_db.py`.
- Run tests: `uv run pytest` (see [architecture/testing.md](architecture/testing.md) for what's covered)

There is no linter, formatter, or type-checker configured anywhere in this repo (no `ruff`, `mypy`, etc. in `pyproject.toml`). `pytest` is present as a dev dependency; most of the app (Qt views, most services) still has no tests.

### Git operations and GitHub pull requests

Do not run `git commit`, `git push`, or create/merge a pull request (via `gh`, the GitHub REST API, or otherwise) — the user handles all of that manually to conserve tokens. Creating a local feature branch is fine. When a chunk of work is done, hand the user a PR title/body draft (Summary + Test plan) so they can commit, push, and open the PR themselves; don't attempt any of those steps.

### Import path convention

Every module uses absolute imports rooted at `src/` (e.g. `from database.session import engine`, `from features.members.menu_view import show_members_view`, `from utils.logger import get_logger`) — never `from src....`. This only resolves when `src/` itself is on `sys.path`, which happens automatically because Python prepends the running script's own directory. In practice this means:
- Always run/debug via `src/main.py` as the entry script (`uv run python src/main.py` from repo root works because `src/` becomes `sys.path[0]`).
- Don't invoke it as `python -m src.main` or import `src` as a package — the internal imports will fail.
- If running an individual module directly for a quick check (e.g. `python src/database/init_db.py`), that also works for the same reason (its own dir's parent isn't added, but `src/` is `sys.path[0]` since the script lives there).

## Directory map

`database/`/`common/`/`ui/`/`utils/` are cross-cutting layers (ORM models, generic table browsing, app shell/chrome, logging); each domain screen lives in its own `features/<domain>/` package (view, toolbar, dialog, and backing services together) — new domains (periods, reports) should follow the `features/members/` shape rather than adding flat files to a `services/` layer. `tests/` sits at the repo root alongside `src/`, not inside it. Full per-file description: [ARCHITECTURE.md](ARCHITECTURE.md).

```
src/
  config.py                 # paths + DB URL
  main.py                   # entry point
  database/
    models.py                # SQLAlchemy ORM models (source of truth for schema)
    session.py                # engine + SessionLocal + get_session() context manager
    audit.py                  # record_log() - shared Log-row helper for write services
    init_db.py                # creates tables from models, migrates known missing columns, seeds
    seed_db.py                # seed_metodos_pago()/seed_all() - fixed metodos_pago rows from README
    db.sql                    # STALE schema dump, see "Schema drift"
  common/
    view_registry.py          # generic table/view discovery + fetch - no production screen calls it; kept as plumbing
  features/
    members/
      menu_service.py          # real search/query logic for the members screen (socios only)
      toolbar_service.py       # CRUD logic for the members toolbar (add/get/update/delete, all audit-logged)
      menu_view.py              # the members screen (search bar, filtros, table)
      toolbar.py                 # QToolBar with Nuevo/Editar/Eliminar/Refrescar/Exportar/Registrar
      dialog.py                   # add/edit member dialog (one class, edit mode via initial_data)
      column_fill.py               # table column-width-fill helper
      table_sort.py                 # 3-state header-click sort mixin
    transactions/
      service.py                  # TransactionsService - lookups, integrity validation, add_transaction, list_transactions
      dialog.py                    # TransactionDialog (+ inline _PeriodoRapidoDialog quick-create)
      toolbar.py                    # Nuevo movimiento/Refrescar/Exportar - no Editar/Eliminar
      view.py                        # standalone Transacciones screen (search + tipo + periodo filters)
    settings/
      menu_view.py              # Ajustes hub: section buttons -> metodos_pago / reglas_cobro / reset
      metodos_pago_*.py           # MetodosPagoService/Dialog/Toolbar/View - CRUD, fixed methods protected from rename/delete
      reglas_cobro_*.py           # ReglasCobroService/Dialog/Toolbar/View - CRUD, no fixed set, every field editable
      reset_service.py           # ResetService - full_reset()/scoped_reset()
      reset_view.py               # type-to-confirm UI for both reset operations
  ui/
    styles.py                  # shared QSS stylesheet strings
    main_window.py              # QMainWindow + QStackedWidget shell
    views/
      main_menu_widget.py        # home screen
      menu_bar.py                 # QMenuBar (File/Edit/View/Help)
  utils/
    logger.py                  # rotating file + stdout logger factory
    text.py                     # normalize_for_match() - shared accent/case-insensitive text normalization
    exporters.py                # EMPTY FILE (0 bytes) — export logic not yet started
```

## Key invariants & durable decisions

These are the cross-cutting rules most likely to cause a real bug or a re-litigated decision if forgotten. Full reasoning for each lives in [architecture/cross-cutting.md](architecture/cross-cutting.md) and the relevant per-file section under `architecture/` (see [ARCHITECTURE.md](ARCHITECTURE.md) for the index).

- **`numero_socio` is a shared family identifier, not unique per `Socio` row.** `Transaccion`/`SaldoSocios` intentionally FK on `numero_socio` (the family); `Log` FKs on `id_socio` (the individual). Don't "fix" this by uniquifying `numero_socio` or switching those FKs.
- **`Socio.es_titular`**: exactly one titular per `numero_socio`, enforced in the app layer (`MembersService`), never at the DB layer. A `numero_socio` group with no titular is blocked from registering transactions everywhere (open picker and the Members "Registrar" shortcut alike) until an admin assigns one via Members.
- **Soft-deactivation only, app-wide.** `Socio.estado`, `MetodoPago.estado`, `ReglaCobro.estado`: "remove" always means `estado="inactivo"`, never a physical `DELETE`. `Transaccion` is the deliberate exception — no `estado`, no edit, no delete at all; once persisted it's a permanent audit-trail entry, and corrections are new transactions (e.g. a `reembolso` against a `cargo`).
- **No Alembic.** Schema changes go directly in `models.py`, applied via `create_all` (additive-only) or a full `data/club_manager.db` delete + `init_db()` rebuild. `database/init_db.py`'s `_add_missing_columns()` is a narrow stopgap for simple single-nullable-column additions only — don't lean on it for anything structural.
- **`db.sql`/`db.md` are stale**, manually-maintained dumps that no longer match `models.py` (e.g. a `forma_pago` column and `transacciones.estado` that don't exist in code). `models.py` is the sole source of truth — never derive code from the docs.
- **Every write service records an audit `Log` row** via `database/audit.py`'s `record_log()`, inside the same `get_session()` transaction as the write it documents (`ResetService.full_reset()` is the one necessary exception, since it drops the `logs` table itself). Writes not attributable to a member pass `id_socio=None`. Follow this pattern for any new write service.
- **Gotcha:** never do `from database.session import engine` (or `SessionLocal`) at module import time in code that needs the raw engine (e.g. `drop_all`/`create_all`) — import inside the function body, or `tests/conftest.py`'s DB-patching fixture won't apply and the code will silently touch the real DB during tests.
- **Table → screen ownership is a deliberate per-table decision**, not a generic browser (`common/view_registry.py` is kept as unused plumbing, not wired to any screen — see [architecture/database.md](architecture/database.md) before reaching for it). `logs` is the one table still without an assigned screen.
- **Single-row-only editing**: every "Editar" action (Members, Métodos de pago, Reglas de cobro) refuses with an info message if more than one row is selected, rather than silently editing the first. Every "Eliminar"/deactivate action requires an explicit confirmation dialog naming the affected row(s) — never a silent/direct path.
- **Feature folders**: a new domain (periods, reports) gets its own `features/<domain>/` package (view+toolbar+dialog+service together), not flat files under a shared `services/` layer.
