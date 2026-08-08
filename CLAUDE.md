# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Desktop management app ("Club Social Paraiso") for a club's members and finances: member records, dues/payments/refunds, per-period balances, and reporting. Built with **PySide6** (Qt) for the UI, **SQLAlchemy** ORM over **SQLite** for persistence. Domain/UI text and identifiers are in Spanish (Socio = member, Transaccion = transaction, Periodo = period, etc.) — match this convention when adding new domain code.

The app is early-stage: the "Gestionar Miembros" (members) screen and a "⚙️ Ajustes" (settings) hub are wired up from the main menu. Within Members, member CRUD (search, create, edit, deactivate) is fully implemented and audit-logged; export and transaction-registration remain logging placeholders (see per-file notes below). Within Ajustes, payment methods (`metodos_pago`) and billing rules (`reglas_cobro`) both have full CRUD, and a database reset action (full wipe + scoped reset) exists — see `features/settings/` below. No other domain screens (transactions, periods, reports) exist yet.

See [README.md](README.md) for the full functional/non-functional requirements spec (in Spanish) and [db.md](db.md) for a mermaid ER diagram of the *intended* schema (note: it has drifted from the actual code — see "Schema drift" below).

## Commands

Dependencies are managed with **uv** (`uv.lock` is present; no `requirements.txt`, no `pip`).

- Install deps: `uv sync`
- Run the app (from repo root): `uv run python src/main.py`
- Initialize/reset the DB schema only: `uv run python src/database/init_db.py` (calls `Base.metadata.create_all` — creates missing tables, does **not** drop/alter existing ones; a small stopgap in `init_db()` (`_add_missing_columns`) ALTERs in the specific columns known to have been added after tables already existed — see its `database/init_db.py` section below — but any other schema change still needs the DB file deleted to fully rebuild). Also seeds the fixed `metodos_pago` rows via `database/seed_db.py`.
- Run tests: `uv run pytest` (see `tests/` below)

There is no linter, formatter, or type-checker configured anywhere in this repo (no `ruff`, `mypy`, etc. in `pyproject.toml`). `pytest` is present as a dev dependency; see `tests/` below for what's actually covered — most of the app (Qt views, most services) still has no tests.

### Import path convention

Every module uses absolute imports rooted at `src/` (e.g. `from database.session import engine`, `from features.members.menu_view import show_members_view`, `from utils.logger import get_logger`) — never `from src....`. This only resolves when `src/` itself is on `sys.path`, which happens automatically because Python prepends the running script's own directory. In practice this means:
- Always run/debug via `src/main.py` as the entry script (`uv run python src/main.py` from repo root works because `src/` becomes `sys.path[0]`).
- Don't invoke it as `python -m src.main` or import `src` as a package — the internal imports will fail.
- If running an individual module directly for a quick check (e.g. `python src/database/init_db.py`), that also works for the same reason (its own dir's parent isn't added, but `src/` is `sys.path[0]` since the script lives there).

## Directory layout and file-by-file reference

The codebase is organized as a hybrid: `database/`/`common/`/`ui/`/`utils/` are cross-cutting layers (ORM models, generic table browsing, app shell/chrome, logging), while each domain screen lives in its own package under `features/` (view, toolbar, dialog, and backing services together). As new domains (transactions, periods, reports) get built out, they should each get their own `features/<domain>/` package following the `features/members/` shape below, rather than adding more flat files to a `services/` layer. `tests/` (pytest suite, see below) sits at the repo root alongside `src/`, not inside it.

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
    view_registry.py          # generic table/view discovery + fetch - no production screen calls it (see PLAN.md 2.16); kept as plumbing
  features/
    members/
      menu_service.py          # real search/query logic for the members screen (socios only)
      toolbar_service.py       # CRUD logic for the members toolbar (add/get/update/delete, all audit-logged)
      menu_view.py              # the members screen (search bar, límite, filtros, table)
      toolbar.py                 # QToolBar with Nuevo/Editar/Eliminar/Refrescar/Exportar/Registrar
      dialog.py                   # add/edit member dialog (one class, edit mode via initial_data)
      column_fill.py               # table column-width-fill helper
      table_sort.py                 # 3-state header-click sort mixin
    settings/
      menu_view.py              # Ajustes hub: section buttons -> metodos_pago / reglas_cobro / reset
      metodos_pago_service.py    # MetodosPagoService - CRUD, fixed methods protected from rename/delete
      metodos_pago_dialog.py      # MetodoPagoDialog - add/rename form (one field: nombre)
      metodos_pago_toolbar.py      # Nuevo/Editar/Activar-Desactivar/Refrescar
      metodos_pago_view.py          # métodos de pago table screen
      reglas_cobro_service.py    # ReglasCobroService - CRUD, no fixed set, every field editable
      reglas_cobro_dialog.py      # ReglaCobroDialog - full rule form (descripcion/cuota/plazo/penalizacion/descuento)
      reglas_cobro_toolbar.py      # Nueva/Editar/Activar-Desactivar/Refrescar
      reglas_cobro_view.py          # reglas de cobro table screen
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

### `src/config.py`
Computes `BASE_DIR` as two levels up from this file (i.e. the repo root, robustly, independent of process `cwd`), derives `DATA_DIR = BASE_DIR / "data"` and creates it (`mkdir(exist_ok=True)`) at **import time**, and builds `DATABASE_URL = f"sqlite:///{DATA_DIR / 'club_manager.db'}"`. This is the authoritative path logic for the DB location.

### `src/main.py`
```python
DB_PATH = DATA_DIR / "club_manager.db"
if not DB_PATH.exists():
    init_db()
```
`DB_PATH` is built from `config.DATA_DIR` (the same absolute, `BASE_DIR`-relative path `session.py`'s engine uses), so this check always agrees with where the SQLAlchemy engine actually points regardless of the process's current working directory. Don't reintroduce a fresh `cwd`-relative `Path("data/...")` here.
`run_main_window()` from `ui/main_window.py` is only invoked under `if __name__ == "__main__"`, so importing `main.py` elsewhere is side-effect-light except for the `init_db()` check above, which runs unconditionally at import time.

### `src/database/models.py`
Declares `Base = declarative_base()` and seven ORM classes. All monetary columns are `Numeric(10, 2)`.

| Model | Table | PK | Notable columns | Relationships |
|---|---|---|---|---|
| `Socio` | `socios` | `id_socio` | `numero_socio` (shared/family id, **not unique**, see below), `nombre`, `apellidos`, `telefono`, `email`, `fecha_alta`, `estado` (default `"activo"`), `observaciones` | `transacciones`, `saldos`, `logs` (all `back_populates`) |
| `MetodoPago` | `metodos_pago` | `id_metodo` | `nombre` (unique), `estado` (default `"activo"` — soft-deactivation, same pattern as `Socio`; added after the table already existed, see `init_db.py`'s migration note) | `transacciones` |
| `Periodo` | `periodo` | `id_periodo` | `nombre`, `fecha_inicio`, `fecha_fin`, `estado` (default `"abierto"`) | `transacciones`, `saldos` |
| `ReglaCobro` | `reglas_cobro` | `id_regla` | `descripcion`, `cuota_mensual`, `plazo_pago`, `penalizacion`, `descuento`, `estado` (default `"activo"` — same soft-deactivation pattern, added the same way as `MetodoPago.estado`) | none (standalone config table; nothing FKs into it yet) |
| `Transaccion` | `transacciones` | `id_transaccion` | `numero_socio` (FK → `socios.numero_socio`), `id_periodo` (FK), `id_metodo` (FK), `tipo` (cargo/pago/reembolso), `monto`, `fecha` (default `date.today`), `referencia` | `socio`, `periodo`, `metodo` |
| `SaldoSocios` | `saldos_socios` | `id_saldo` | `numero_socio` (FK), `id_periodo` (FK), `saldo_anterior`, `cargos`, `pagos`, `saldo_actual` (all default `0`); `UniqueConstraint(numero_socio, id_periodo)` — one balance row per member-family per period | `socio`, `periodo` |
| `Log` | `logs` | `id_log` | `id_socio` (FK → `socios.id_socio`, **not** `numero_socio`), `accion`, `tabla_afectada`, `id_registro_afectado`, `descripcion_cambio`, `fecha_hora` (default `datetime.now`) | `socio` |

**Important nuance (explicitly called out in a code comment on `Socio.numero_socio`):** `numero_socio` is a shared family/household identifier and is **not unique per `Socio` row** — multiple family members can share one `numero_socio`. `Transaccion` and `SaldoSocios` intentionally FK against `numero_socio` (the family), not `id_socio` (the individual). `Log`, by contrast, FKs against `id_socio` (the individual). Don't "fix" this by making `numero_socio` unique or by switching `Transaccion`/`SaldoSocios` to FK on `id_socio` — it's deliberate.

No Alembic/migration tooling exists — schema changes are made directly in `models.py` and applied via `create_all` (additive only) or by deleting `data/club_manager.db` and re-running `init_db()`. The one exception is columns explicitly listed in `init_db.py`'s `_add_missing_columns()` stopgap (currently `MetodoPago.estado` and `ReglaCobro.estado`), which get an `ALTER TABLE ADD COLUMN` on an existing DB — see that file's section below. Don't rely on this for anything beyond adding a single nullable/defaulted column; it's not a real migration system.

### `src/database/session.py`
`echo` is no longer hardcoded — it reads `_ECHO = os.environ.get("CLUBAPP_DB_ECHO", ...)`, so verbose SQL logging is opt-in (`CLUBAPP_DB_ECHO=1`) instead of always-on. A `connect` event listener sets `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` on every new connection so reads (the table/view browser) aren't blocked behind an in-progress write; it deliberately does **not** set `PRAGMA foreign_keys=ON` (see the docstring — enabling it makes SQLite reject the intentional non-unique `numero_socio` FK relationship). `SessionLocal` (the raw sessionmaker) is still exported, but the preferred way to write is the `get_session()` context manager defined here: it yields a `Session`, commits on success, rolls back and re-raises on exception, and always closes — every `MembersService` method in `features/members/toolbar_service.py` (`add_member`, `get_member`, `update_member`, `delete_members`) uses it, as does every method on `features/settings/`'s `MetodosPagoService`, `ReglasCobroService` and `ResetService.scoped_reset`. `view_registry.py` still talks to the DB via raw `engine.connect()` + `text()`, not the ORM session.

**Gotcha for anything that needs the raw `engine` itself** (not just a `Session`) — e.g. `ResetService.full_reset()`'s `Base.metadata.drop_all()`/`create_all()` calls: don't do `from database.session import engine` at module import time. That binds the name once, at import, before `tests/conftest.py`'s `test_engine` fixture has a chance to monkeypatch `database.session.engine` to a throwaway test DB (the exact gotcha already documented for `view_registry.py` below) — a module-level import would silently point at the real `data/club_manager.db` in every test. Do the `from database.session import engine` import *inside* the function body instead, so it re-resolves whatever's currently bound each time it's called.

### `src/database/audit.py` — `record_log()`
A single shared helper, `record_log(session, *, id_socio, accion, tabla_afectada, id_registro_afectado, descripcion_cambio)`, that adds a `Log` row to an already-open `Session` (it does not commit). Every `MembersService` write method calls it from inside its own `with get_session() as session:` block, before that block exits — so the write and its audit-log row commit (or roll back) together in one transaction, never as two separate DB round-trips that could diverge on failure. `id_socio`/`id_registro_afectado` are the individual's `id_socio` (matching `Log`'s FK target — see the `models.py` note on why `Log` differs from `Transaccion`/`SaldoSocios` here, which FK on `numero_socio` instead). There's no actor/user column on `Log` and no multi-user auth in the app yet, so entries record *what* changed, not *who* changed it. Building a screen to *read* these logs back is a separate, still-open concern — see `common/view_registry.py`'s note and PLAN.md 2.16's table on `logs`.

`features/settings/`'s services (`MetodosPagoService`, `ReglasCobroService`, `ResetService`) call it the same way, but always pass `id_socio=None` — `metodos_pago`/`reglas_cobro`/reset changes aren't attributed to a member, and `Log.id_socio` is nullable specifically to allow this. `ResetService.full_reset()` is the one exception to "always inside the write's own transaction": since it drops and recreates every table (the `logs` table included), it can only write its `"reset_completo"` Log row *after* recreation, as the very first row in the fresh table, not atomically with the wipe itself.

### `src/database/seed_db.py`
`METODOS_PAGO_FIJOS` is the list of the 5 payment methods README.md's "Formas de Pago" section fixes (REMESA, EFECTIVO, TRANSFERENCIA, TRANSFERENCIA/EFECTIVO, INACTIVO). `seed_metodos_pago()` reads the existing `metodos_pago.nombre` values via `get_session()` and inserts only whichever of those 5 aren't already present — idempotent, so it's safe to call on every startup, not just once on a brand-new DB; a DB a developer partially populated by hand is left alone beyond filling in what's missing. `seed_all()` wraps it (a home for future seed steps to join — `reglas_cobro` deliberately isn't seeded here, since billing rules are club-defined config, not a README-fixed set). Called from `init_db()`.

### `src/database/init_db.py`
`init_db()` now does three things in order: `Base.metadata.create_all(bind=engine)`, then `_add_missing_columns()`, then `seed_db.seed_all()`. `_add_missing_columns()` is a minimal stopgap for the fact that `create_all` never alters an existing table: it's a small `(table, column, ALTER TABLE ... ADD COLUMN ddl)` list (currently `metodos_pago.estado` and `reglas_cobro.estado`), and for each one checks `PRAGMA table_info(<table>)` and only runs the `ALTER TABLE` if the column is actually missing — safe to call on every startup, a no-op once every column exists. This is not a general migration system (see the `models.py` "No Alembic" note above) — extend this list only for simple, single-nullable-column additions; anything more structural still means deleting `data/club_manager.db` and re-running `init_db()`.

### `src/database/db.sql` and `db.md` — Schema drift (read before trusting either)
Both are **manually-maintained reference dumps that no longer match `models.py`**, and neither is generated from the ORM. Concretely:
- `db.sql`'s `socios` table has a `forma_pago VARCHAR` column with `FOREIGN KEY(forma_pago) REFERENCES metodos_pago (id_metodo)` — this column **does not exist** on `Socio` in `models.py`.
- `db.sql`'s `transacciones` table has an `estado VARCHAR` column — **not present** on `Transaccion` in `models.py`.
- `db.md`'s mermaid diagram uses `id_usuario`/`usuarios` naming instead of the actual `id_socio`/`socios` used in code, and lists fields (e.g. `saldos_usuarios.id_saldo`) that only loosely match the real `saldos_socios` table.
- Treat `models.py` as the single source of truth. If you update the schema, consider updating `db.sql`/`db.md` too for documentation purposes, but do not derive code from them.

### `src/common/view_registry.py` — `ViewRegistry`
Central mechanism for generic, DB-driven table browsing. **As of PLAN.md 2.16, no production screen calls this anymore** — the Members screen's "Vistas" dropdown (its only caller) was removed because it exposed every DB table, including internal ones like `logs`, as a raw unformatted dump with no design intent. The class itself was **deliberately kept** (decided, not deleted) as cross-cutting plumbing for whatever future screen wants generic table/SQL/callable lookup by name; its only current consumer is its own test file (`tests/test_view_registry.py`). Don't wire a new screen to it without first checking whether a purpose-built query (like `MembersMenuService`'s) is a better fit — see the mapping table in PLAN.md 2.16 for where each table is meant to surface.
- `__init__` calls `get_db_tables()` (via `sqlalchemy.inspect(engine).get_table_names()`) and auto-registers every table as a `"table"`-type view via `register_table_view` (swallows exceptions so a broken inspector doesn't crash construction).
- Also supports `register_sql_view(name, sql, description)` (arbitrary `SELECT`) and `register_callable_view(name, func, description)` (a zero-arg callable returning `(keys, rows)`) for future non-table-backed views — neither is currently used by any call site, but the plumbing exists.
- `fetch_table(table_name, limit)`: validates the table exists, builds `SELECT * FROM "<table>"` (optionally `LIMIT :limit` via a bound parameter — safe from injection for the limit value), executes via a raw `engine.connect()`, returns `(keys, rows)`. `limit=0` is normalized to "no limit" (`None`).
- `fetch_view(name, limit)`: dispatches on the registered type (`table`/`sql`/`callable`); for `sql`-type views it tries `f"{sql} LIMIT :limit"` first and falls back to the raw unlimited SQL if that fails (e.g. if the SQL already has a trailing clause `LIMIT` can't just be appended to). **Caution**: `table_name`/`sql` values are interpolated directly into the query string via an f-string (not parameterized) — safe today because table names only ever come from `inspector.get_table_names()`, not user input, but don't extend this to accept arbitrary user-supplied table/SQL strings without adding validation.
- All methods catch broad `Exception`, log via `logger.exception(...)`, and return empty results rather than raising — callers never need to handle exceptions from this class, but failures are silent unless you check the logs.

### `tests/` — pytest suite
Run with `uv run pytest` from the repo root. `pyproject.toml`'s `[tool.pytest.ini_options]` sets `pythonpath = ["src"]` (so tests use the same absolute imports as the app, e.g. `from database.models import Socio`) and `testpaths = ["tests"]`.

`conftest.py`'s `test_engine` fixture is the one piece of infrastructure every DB-touching test depends on: it creates a throwaway per-test SQLite file (via pytest's `tmp_path`) with all tables created from `Base.metadata`, then monkeypatches it into **both** `database.session.engine`/`SessionLocal` **and** `common.view_registry`'s separately-imported `engine` name. This second patch is required because `view_registry.py` does `from database.session import engine`, which binds its own module-level reference at import time — patching only `database.session.engine` would leave a constructed `ViewRegistry` still pointed at the real `data/club_manager.db`. **If a future module imports `engine` (or `SessionLocal`) by name the same way, add the same explicit patch to this fixture, or its tests will silently read/write the real DB instead of the isolated one.**

`pytest-qt` is **not** installed — no test so far needs a live `QApplication` (the sort-key helpers in `table_sort.py` are plain functions on the mixin, exercised without instantiating any Qt widgets). Add `pytest-qt` only once a test actually requires one.

Current coverage: `MembersService.add_member`/`get_member`/`update_member`/`delete_members` (persistence, NOT NULL rollback, shared-`numero_socio` semantics, and the `Log` row each write produces via `record_log` - `tests/test_members_service.py`); `MembersMenuService.search_members` (matching by each field, case/accent insensitivity, limit handling, empty-filter-means-everyone semantics - `tests/test_members_menu_service.py`); `ViewRegistry` (table auto-registration, `fetch_table`/`fetch_view` across all three view types, limit handling - still tested despite having no production caller, see its `common/view_registry.py` note); `TableSortMixin._normalize_for_sort`/`_make_sort_key` (accent/casefold normalization, numeric-vs-text key ordering) in `features/members/table_sort.py`; `seed_metodos_pago` (inserts-all-when-empty, idempotent on re-run, only-fills-missing, leaves custom methods alone - `tests/test_seed_db.py`); `MetodosPagoService` (list/add/rename/estado-toggle, fixed-method rename protection, audit-log rows - `tests/test_metodos_pago_service.py`); `ReglasCobroService` (same CRUD shape, multiple named rules coexisting - `tests/test_reglas_cobro_service.py`); and `ResetService.full_reset`/`scoped_reset` (full wipe clears every table and re-seeds `metodos_pago` with exactly one fresh Log row; scoped reset clears only `transacciones`/`saldos_socios`/`periodo` while `socios`/`reglas_cobro`/existing log history survive - `tests/test_reset_service.py`). Nothing else in the app has tests yet — no Qt view/dialog/toolbar tests (the settings screens were instead verified manually with ad-hoc `QT_QPA_PLATFORM=offscreen` scripts during development, not committed as pytest), no coverage of exports/transaction-registration, no balance-calculation tests (that logic doesn't exist yet).

### `src/features/members/menu_service.py` — `MembersMenuService`
A members-only service now — it no longer owns a `ViewRegistry` or exposes any generic table-browsing methods (`get_db_tables`/`get_views`/`fetch_view`/`fetch_table` were removed with the "Vistas" dropdown, PLAN.md 2.16).
- `search_members(text, model, limit)`: real query — fetches every `Socio` row via `database.session.get_session()` (`_fetch_socios_rows`), then filters in Python (`_filter_socio_rows`) by substring match against `numero_socio`/`nombre`/`apellidos`/`email`, accent- and case-insensitively (`utils.text.normalize_for_match`, shared with `TableSortMixin`'s sort-key normalization). **Empty/whitespace-only `text` means "no filter"** — every socio is returned (subject to `limit`) — which is also how `MembersMenuView.load_table_view()`'s default table load gets its data (it calls this with `text=""`). Deliberately does not filter by `estado`, so deactivated members stay searchable/visible until estado-aware filtering/display is built (PLAN.md 2.2). Populates the model via `_populate_model` (rebuilds column count/headers/rows from scratch) and returns the row count.
- `get_filter_labels(model)`: reads header text off each column of a Qt model (used to populate the "Filtros" show/hide-column menu) — pure UI-data extraction, tolerant of `None` headers.

### `src/features/members/toolbar_service.py` — `MembersService`
UI-decoupled backend for the members toolbar. Member CRUD (`add_member`/`get_member`/`update_member`/`delete_members`) is fully implemented; `export_members`/`register_transactions` remain logging placeholders. Every write method calls `database.audit.record_log` inside its own `get_session()` block, so the write and its `Log` row commit/roll back together (see `database/audit.py`'s note above).
- `add_member(data)`: creates a `Socio` row via `get_session()`, records a `"crear"` log, and returns its new `id_socio`, or `None` on failure.
- `get_member(id_socio)`: fetches one member's editable fields (`numero_socio`/`nombre`/`apellidos`/`telefono`/`email`/`fecha_alta`/`estado`/`observaciones`) as a plain dict shaped like `MemberDialog.get_data()`'s return value — used to pre-populate the edit dialog with fresh DB data rather than trusting the Qt table's (possibly reordered/stale) cell text. Returns `None` if the member doesn't exist.
- `update_member(id_socio, data)`: persists edits via `get_session()`. Before applying `data`, diffs each field against the current DB value and records a `"editar"` log listing only the fields that actually changed (e.g. `"nombre: 'Marta' -> 'Marta A'"`) — untouched fields aren't mentioned. Returns `True`/`False`; `False` on unknown id or a DB error (e.g. NOT NULL violation), with nothing persisted (write and log both roll back together).
- `delete_members(selected_indices, model_getter)`: **soft-delete only, never a physical `DELETE`** — for each selected row it reads column-0 (`id_socio`) via `model_getter`, updates that `Socio.estado = "inactivo"`, and records a `"desactivar"` log, all via one `get_session()` block per row. **Decided (durable):** "Eliminar" in the members toolbar always means deactivation via `UPDATE estado = "inactivo"`, so transaction/balance/log history referencing the member is preserved — a physical `DELETE FROM socios` path is not planned. Returns the row indices (deduped, sorted descending) that were successfully deactivated; `MembersToolBar.on_delete_member` then calls `model.removeRow(r)` on those for immediate UI feedback. Since nothing filters by `estado` yet, a deactivated member still reappears (now correctly marked `estado="inactivo"`) the next time the view is reloaded — estado-aware filtering/display is still unbuilt (the confirmation dialog itself is now built, see `MembersToolBar` below).
- `export_members(rows, destination)`: logs the row count and destination; no file is written. Pairs with `utils/exporters.py`, which is currently an **empty file** — implementing export means starting there.
- `register_transactions(selected_indices)`: logs selected indices or "opening general register" if none selected; no dialog/persistence yet.

### `src/utils/logger.py`
- `LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"` (also repo-root-relative and robust, like `config.py`) → `data/logs/app.log`.
- `_configure_logger(name)`: sets level `INFO`, attaches a `RotatingFileHandler` (5 MB × 3 backups, UTF-8) and a `StreamHandler` to stdout, and sets `propagate = False` (so messages don't double-log through the root logger). Guards against re-adding handlers if the logger already has any.
- Module-level `logger = _configure_logger("clubapp")` is created but not exported/used directly elsewhere.
- `get_logger(name)` returns a `clubapp.<name>` child logger, lazily configuring it the first time. Every other module does `logger = get_logger(__name__)` at import time — follow this exact pattern for any new module instead of `print()` or ad-hoc `logging.getLogger()`.

### `src/utils/exporters.py`
Completely empty (0 bytes) — no exports, no stub function, nothing. This is where Excel/PDF export (per the README's "Exportar reportes a Excel/PDF" requirement) would presumably live; no export library (e.g. `openpyxl`, `reportlab`) is currently in `pyproject.toml`'s dependencies.

### `src/ui/styles.py`
Four `Final[str]` constants: `MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET`, `SETTINGS_MENU_STYLESHEET` (Qt QSS strings), plus two small inline-style snippets `TITLE_STYLE`/`BUTTON_FONT_STYLE`. `MEMBERS_MENU_STYLESHEET` includes a `#resultsTable QHeaderView::section { color: #000000; }` rule so header text stays black. `SETTINGS_MENU_STYLESHEET` is a near-duplicate of `MEMBERS_MENU_STYLESHEET` scoped under `#settingsMenu` instead of `#membersMenu` (same paper background/`#backButton`/`#resultsTable` rules) — a deliberate small duplication rather than a shared token layer, since that refactor is deferred to the UI-polish pass in `UI_PROPOSAL.md`/PLAN.md 4.3. All three of `SettingsView`, `MetodosPagoView`, `ReglasCobroView` and `ResetView` share `SETTINGS_MENU_STYLESHEET` (multiple widgets with the same `objectName` is valid Qt — QSS ID selectors just match every widget with that name). Remember QSS only supports `/* ... */` comments — a `#`-prefixed "comment" is silently parsed as a malformed ID-selector block instead of being ignored, which is how a prior version of a header-color rule went dead without erroring.

### `src/ui/main_window.py`
`MainWindow(QMainWindow)`: sets title "AppClub", resizes to 900×600, creates a `QStackedWidget` as central widget, adds a `MainMenuWidget` (stored as `self._home`) as the first page, and attaches a `MainMenuBar`. `run_main_window(argv)` builds the `QApplication`, shows the window, and runs `app.exec()`. Deliberately has no GUI side effects at import time (per its own docstring) so it stays importable for future tests/tooling.

### `src/ui/views/menu_bar.py` — `MainMenuBar(QMenuBar)`
Builds a standard File/Edit/View/Help menu bar and self-attaches via `main_window.setMenuBar(self)`.
- **File**: New/Open/Save (all wired to `not_implemented(name)`, which pops a `QMessageBox.information`), a separator, then Exit (`Ctrl+Q`, wired to `main_window.close`, actually functional).
- **Edit**: Undo/Redo/Cut/Copy/Paste — all `not_implemented`.
- **View**: "Toggle Fullscreen" (`F11`) — actually functional, calls `toggle_fullscreen` which flips between `showFullScreen()`/`showNormal()`.
- **Help**: "About" — actually functional, shows a `QMessageBox.about` with a hardcoded credit ("Desarrollado por Sergio Alfonso Gutierrez", "Versión 1.0").
Only Exit / Toggle Fullscreen / About are real; everything else in this menu bar is an explicit `not_implemented` stub by design (not a bug).

### `src/ui/views/main_menu_widget.py` — `MainMenuWidget(QWidget)`
The home screen. Title label with a drop-shadow effect, then a 2-column `QGridLayout` of buttons built from a hardcoded list:
- `"🧑‍🤝‍🧑 Gestionar Miembros"` → wired to `show_members_view(self.main_window)` (functional, navigates to the members screen).
- `"⚙️ Ajustes"` → wired to `show_settings_view(self.main_window)` (functional, navigates to the Settings hub — see `features/settings/menu_view.py` below).
Button wiring is done by matching on the button's emoji prefix (`button.startswith("🧑‍🤝‍🧑")` / `startswith("⚙️")`) inside the loop that creates them — if you add a new home-menu button, follow this same emoji-prefix-dispatch pattern or refactor it, but be aware this is how routing currently works here.
Also defines `show_home()`, a convenience to switch the stack back to itself — but nothing currently calls it (back-navigation is instead handled by `MembersMenuView.on_back_to_main_menu`, which reaches into `main_window._stack`/`main_window._home` directly).

### `src/features/members/menu_view.py` — `MembersMenuView(QWidget)`
The largest and most complex file in the codebase. Layout, top to bottom:
1. **Top bar** (`#topBar`): left = "Volver" back button (`on_back_to_main_menu`, switches the stack to `main_window._home`); center = search `QLineEdit` (`self.search_input`, placeholder "Buscar miembros, email, id...") + "Buscar" button, both wired to `on_search`; middle = a "Límite:" numeric `QLineEdit` (`self.limit_input`, `QIntValidator(0, 99999)`, default text `"0"`, Enter triggers `on_limit_changed`); right = one `QToolButton` with a popup menu — "Filtros" (`self.filters_menu`, checkable per-column show/hide actions built by `_populate_filters_menu()`). **The old "Vistas" table-picker `QToolButton`/menu that used to sit next to Filtros is gone** (PLAN.md 2.16) — Members only ever shows socios now.
2. **Toolbar**: a `MembersToolBar` instance (see below), given references to the table/model via `set_table_references`.
3. **Central area**: a `QTableView` (`self.table`) backed by a `QStandardItemModel` (`self.model`, starts as 0 rows × 4 cols). Header uses `Interactive` resize mode (user-draggable) with `setDefaultSectionSize(120)`; sorting and moving of sections are enabled manually rather than via Qt's built-in sort-on-click.

Key behaviors:
- **Auto-load on construction**: after wiring everything up, it calls `self.load_table_view()` directly (wrapped in `try/except: pass`) — there's nothing to choose between anymore, so the old "find a view named socios, else fall back to the first registered view" logic (which read from `ViewRegistry` via the service) is gone.
- **`get_limit()`**: parses `limit_input` text; empty/`0`/parse-error all mean "no limit" (`None`); otherwise clamps to `[1, 99999]`.
- **`on_search()`**: delegates to `MembersMenuService.search_members` (real DB query, see above) and remembers `self._last_search_text` for later sort-clearing restoration.
- **`load_table_view()`**: the real DB-load path, **no longer takes a `table_name` argument** — it always calls `MembersMenuService.search_members("", ...)` (i.e. "no filter", every socio). Sets `self._current_view_name = "socios"` (kept only so `TableSortMixin` has something truthy to check before reloading on sort-clear), repopulates the filters menu, re-applies any active sort (`_maybe_reapply_sort`), and re-runs `ensure_columns_fill()`.
- **`refresh_table()`**: just calls `load_table_view()` — the old "reload the currently selected view, else fall back to the registry's first view" branching is gone since there's only ever one table to reload now. This is what `MembersToolBar`'s "Refrescar" action calls via duck-typing (`hasattr(parent, "refresh_table")`), and what `on_limit_changed()` calls unconditionally on Enter in the límite field.
- **Custom column-fill logic (`ensure_columns_fill`)**: rather than Qt's `Stretch` resize mode (which disables interactive resizing), this manually distributes any leftover viewport width proportionally across visible columns on each resize (hooked via an `eventFilter` on `self.table.viewport()`, listening for `QEvent.Type.Resize`) — chosen specifically to keep columns both interactively resizable *and* filling available width. If you touch table sizing, understand this custom mechanism before reaching for `QHeaderView.ResizeMode.Stretch`.
- **Custom 3-state sort (`_on_header_clicked` → `_apply_sort`/`_clear_sort`)**: clicking a header cycles ascending → descending → unsorted (not Qt's built-in `sortByColumn`). Sorting is done in Python by reading every cell's text out of the model, sorting the plain rows, and rebuilding the model from scratch (`_make_sort_key` prefers numeric comparison when a cell parses as int/float, else falls back to `_normalize_for_sort`, which delegates to `utils.text.normalize_for_match` — strips accents via `unicodedata` NFKD normalization and casefolds, so "Álvaro" sorts next to "Alvaro"). Clearing sort restores data by re-running `load_table_view()` (no argument now) rather than keeping a cached "original order" — so a slow/failing DB fetch will also slow down/break "un-sorting".
- **`show_members_view(main_window)`** (module-level function): the singleton-view navigation helper described in the architecture section — creates one `MembersMenuView` cached as `main_window._members_view`, adds it to `main_window._stack` once, and calls `setCurrentWidget` on every call thereafter.
- Several handlers wrap logic in bare `try/except Exception: pass` (e.g. the initial `load_table_view()` call, `ensure_columns_fill()` calls) — failures here are silently swallowed with no log line, unlike most of the rest of the codebase which logs exceptions. Be aware when debugging that some errors in this file produce no trace at all.

### `src/features/members/toolbar.py` — `MembersToolBar(QToolBar)`
Non-movable toolbar, 18×18 icons, actions built from Qt's built-in `QStyle.SP_*` standard icons (no custom icon assets in the repo): Nuevo (`SP_FileIcon`) → `on_add_member`; Editar (`SP_DialogApplyButton`) → `on_edit_member`; Eliminar (`SP_TrashIcon`) → `on_delete_member`; separator; Refrescar (`SP_BrowserReload`) → `on_refresh`; Exportar (`SP_DialogSaveButton`) → `on_export`; Registrar (`SP_DialogOpenButton`) → `on_register_movements`. Takes an optional `MembersService` (defaults to constructing its own). `set_table_references(table, model)` is called by the parent view right after construction so the toolbar can read selection/model state without owning it.
- `on_add_member`: opens `MemberDialog()` (create mode, no `initial_data`); on Accept, calls `MembersService.add_member` and, on success, `parent.refresh_table()`; on failure, a `QMessageBox.critical`.
- `on_edit_member`: resolves the selected row's `id_socio` from column 0, calls `MembersService.get_member(id_socio)` to fetch **fresh DB data** (not the Qt table's cell text, which could be stale/reordered), opens `MemberDialog(self, initial_data=data)` (edit mode — see `dialog.py` below), and on Accept calls `MembersService.update_member(id_socio, dialog.get_data())` then `parent.refresh_table()`. Shows `QMessageBox.information`/`critical` for no-selection/no-such-member/update-failed cases respectively.
- `on_delete_member`: reads selected row indices; if none, shows `QMessageBox.information`. Otherwise calls `_confirm_deactivation(rows)` — a `QMessageBox.question` naming the selected member(s) by nombre/apellidos (read from the currently loaded model's columns 2/3), phrased singular vs. plural, explicitly saying "se marcará como inactivo" (never data loss) — and only proceeds to `MembersService.delete_members` (plus `self.model.removeRow(r)` for each confirmed row) if the user answers Yes. **Decided (durable, PLAN.md 2.2/4.3):** deactivation always requires this confirmation step; there is no direct/silent path.
- `on_refresh`: prefers `parent.refresh_table()` when the parent view exposes one; otherwise logs and no-ops (deliberately does not fall back to inserting demo/sample rows).
- `on_export`: flattens the current model into `list[list[str]]` (missing items become `""`) and passes to `MembersService.export_members` — currently a no-op logger call.

### `src/features/members/dialog.py` — `MemberDialog(QDialog)`
One dialog class handles both create *and* edit — there is no separate `EditMemberDialog`. `__init__(self, parent=None, initial_data: Optional[dict] = None)`: passing `initial_data` (same shape as `get_data()`'s return value) switches the window title to "Editar miembro" and calls `_populate(initial_data)` to fill every field (including mapping `estado` to the matching `QComboBox` index and `fecha_alta` to a `QDate`); omitting it keeps "Nuevo miembro" behavior unchanged. `get_data()` is unchanged and used identically by both callers (`MembersToolBar.on_add_member`/`on_edit_member`) — validation (`numero_socio`/`nombre`/`apellidos` required) is shared too.

### `src/features/settings/menu_view.py` — `SettingsView` (the Ajustes hub)
A landing screen, not a table — back button + title + a small `QGridLayout` of section buttons ("💳 Métodos de pago", "📋 Reglas de cobro", "🗑️ Restablecer base de datos"), the same idea as `MainMenuWidget`'s top-level buttons but one level down. Each button calls a section's own `show_*_view(main_window)` helper. `show_settings_view(main_window)` is the module-level singleton-navigation function (identical pattern to `show_members_view`): caches one `SettingsView` as `main_window._settings_view`, adds it to `main_window._stack` once, `setCurrentWidget` thereafter. Wired from `MainMenuWidget`'s "⚙️ Ajustes" button (previously a no-op that only logged the click).

### `src/features/settings/metodos_pago_service.py` — `MetodosPagoService`
`is_fixed(nombre)` checks membership in `seed_db.METODOS_PAGO_FIJOS`. `list_metodos_pago()` returns every row (any `estado`) as plain dicts with a computed `"fijo"` bool. `add_metodo_pago(nombre)`/`rename_metodo_pago(id, nuevo_nombre)`/`set_metodo_pago_estado(id, estado)` all go through `get_session()` and call `record_log` (see `audit.py` note above) — `rename_metodo_pago` refuses and returns `False` if `is_fixed()` is true for the *current* name, without raising; `set_metodo_pago_estado` has no such restriction, so fixed methods can be deactivated (just never renamed or removed from the fixed set). **Decided (durable):** the 5 README-fixed methods can never be renamed or physically deleted, but can be deactivated like any custom method; custom methods (e.g. Bizum) are fully editable. **Decided (durable):** no method is ever a physical `DELETE` — "remove" always means `estado="inactivo"`, same pattern as `Socio` (nothing FKs into `metodos_pago` yet, so a hard-delete-with-in-use-guard wasn't needed; revisit once `Transaccion` rows can reference one).

### `src/features/settings/metodos_pago_dialog.py` — `MetodoPagoDialog`
One field (`nombre`). Same create/edit dual-mode shape as `MemberDialog`: pass `initial_nombre` for "rename" mode, omit for "new method" mode. `MetodosPagoToolBar` is responsible for never opening this in rename mode for a fixed method (see below) — the dialog itself doesn't know about the fixed set.

### `src/features/settings/metodos_pago_toolbar.py` — `MetodosPagoToolBar`
Nuevo/Editar/"Activar/Desactivar"/Refrescar, same `QToolBar` shape as `MembersToolBar`. `on_edit_metodo` checks `service.is_fixed(nombre_actual)` before opening `MetodoPagoDialog` and shows a `QMessageBox.information` instead if true. `on_toggle_estado` reads the selected row's current `estado` column text, flips it, and — mirroring `MembersToolBar._confirm_deactivation` — asks a `QMessageBox.question` only when the new state is `"inactivo"` (deactivating), never when reactivating.

### `src/features/settings/metodos_pago_view.py` — `MetodosPagoView`
The actual table screen (ID/Nombre/Estado/Tipo columns, `"Tipo"` = `"Fijo"`/`"Personalizado"` computed from `is_fixed`). Small-grid shape, no search/límite/sort composition (unlike `MembersMenuView`) — per `UI_PROPOSAL.md`'s guidance that `metodos_pago`/`reglas_cobro` are low-row-count config grids, not full data screens. Its back button (`on_back_to_settings`) returns to the Settings hub (`main_window._settings_view`), **not** the main menu — it's nested one level under Ajustes. `show_metodos_pago_view(main_window)` is the same singleton-navigation pattern, cached as `main_window._metodos_pago_view`.

### `src/features/settings/reglas_cobro_service.py` — `ReglasCobroService`
Same shape as `MetodosPagoService` but simpler: no fixed set at all (**decided, durable:** the club can define multiple named billing rules — `descripcion` doubles as the name, e.g. "Cuota general" vs. "Cuota reducida" — every field on every rule stays fully editable). `list_reglas_cobro()`/`get_regla_cobro(id)`/`add_regla_cobro(data)`/`update_regla_cobro(id, data)` (full-form update, diffs changed fields into the audit log like `MembersService.update_member`)/`set_regla_cobro_estado(id, estado)`. **Decided, durable:** same soft-deactivation-only pattern as `MetodoPago` — "remove" is `estado="inactivo"`, never a physical `DELETE`.

### `src/features/settings/reglas_cobro_dialog.py` — `ReglaCobroDialog`
Five fields: `descripcion*`, `cuota_mensual`/`penalizacion`/`descuento` (currency, `QDoubleValidator` pinned to the `QLocale.c()` — i.e. `.`-decimal — locale so parsing doesn't depend on the OS locale), `plazo_pago` (days, `QIntValidator`). `get_data()` returns `decimal.Decimal`/`int`/`None` values ready for `ReglaCobro(**data)`. Same create/edit dual-mode shape (`initial_data`) as `MemberDialog`/`MetodoPagoDialog`.

### `src/features/settings/reglas_cobro_toolbar.py` — `ReglasCobroToolBar`
Nueva/Editar/"Activar/Desactivar"/Refrescar. Unlike `MetodosPagoToolBar`, `on_edit_regla` has no fixed-method-style guard — every rule is always editable. `on_toggle_estado` follows the identical confirm-only-when-deactivating rule as `MetodosPagoToolBar`.

### `src/features/settings/reglas_cobro_view.py` — `ReglasCobroView`
Same small-grid shape as `MetodosPagoView` (ID/Descripción/Cuota mensual/Plazo (días)/Penalización/Descuento/Estado columns), same back-to-hub navigation, same `show_reglas_cobro_view(main_window)` singleton pattern (cached as `main_window._reglas_cobro_view`).

### `src/features/settings/reset_service.py` — `ResetService`
`full_reset()`: `Base.metadata.drop_all(bind=engine)` + `create_all(bind=engine)` (imports `engine` from `database.session` *inside* the method — see the "Gotcha" callout in the `session.py` section above), then `seed_db.seed_all()`, then one `record_log` call into the now-empty `logs` table documenting the reset itself (`accion="reset_completo"`). Never touches `data/club_manager.db` as a file (no `os.remove`) — sidesteps Windows file-locking/WAL concerns entirely. `scoped_reset()`: row-deletes `Transaccion`/`SaldoSocios`/`Periodo` inside one `get_session()` block (leaving `Socio`/`MetodoPago`/`ReglaCobro`/existing `Log` rows untouched) and records an `accion="reset_parcial"` log the normal way. **Decided, durable (PLAN.md 2.15):** both a full wipe and a scoped reset are supported — full wipe is "start over," scoped reset is "discard this season's financial activity but keep membership/config."

### `src/features/settings/reset_view.py` — `ResetView`
No table — two `QGroupBox` panels, one per operation, each gated by its own type-to-confirm `QLineEdit` (button starts `setEnabled(False)`, a `textChanged` handler enables it only on an *exact* string match) plus a final `QMessageBox.question` before the service call fires. **Decided, durable (PLAN.md 2.15, explicitly requested as "very safe"):** never a single dismissable dialog. The two operations use deliberately different confirmation phrases (`"REINICIAR"` for scoped, `"BORRAR TODO"` for full) and different button colors (amber `#B8862B` vs. danger red `#A1382F`, inline `setStyleSheet` rather than the shared QSS) specifically so they can't be mis-clicked for each other. Both text fields clear themselves (re-disabling their button) after a reset attempt, successful or not. `show_reset_view(main_window)` is the same singleton pattern, cached as `main_window._reset_view`.

## Cross-cutting notes

- **Encoding/locale**: sorting and DB text search both normalize Spanish diacritics through the same function — `utils.text.normalize_for_match` (accent-strip via `unicodedata` NFKD + casefold), used by `TableSortMixin._normalize_for_sort` and `MembersMenuService._filter_socio_rows`. Keep using this shared helper for any new text-comparison code instead of writing a second accent-normalization implementation.
- **Error handling style**: most services/UI code catches broad `Exception`, logs via `logger.exception(...)`/`logger.warning(...)`, and returns a safe empty/default value rather than propagating — match this style for consistency, but note the `menu_view.py` exceptions to it called out above.
- **Audit logging**: every write service (`MembersService`; `features/settings/`'s `MetodosPagoService`, `ReglasCobroService`, `ResetService`) records a `Log` row via `database.audit.record_log`, in the same DB transaction as the write it documents (`ResetService.full_reset()` is the one necessary exception — see its note above, since the wipe itself removes the `logs` table before it can be re-populated). This is the pattern to follow for any new write service (transactions, periods): call `record_log` from inside the same `get_session()` block, don't write logs as a separate step. Writes not attributable to a specific member (settings changes, resets) pass `id_socio=None` — `Log.id_socio` is nullable for exactly this.
- **Soft-deactivation, not physical deletion, is the app-wide pattern**: `Socio.estado`, `MetodoPago.estado` and `ReglaCobro.estado` all follow the same rule — "remove" in the UI always means `UPDATE estado = "inactivo"`, never `DELETE FROM ...`, so anything that already referenced a row (transactions, logs, balances) keeps a meaningful name even after it's retired. Follow this same pattern for any future entity a user can "remove" (e.g. `Periodo`) rather than reaching for a physical delete.
- **Seed data**: `database/seed_db.py`'s `seed_metodos_pago()` (idempotent, run from `init_db()` on every startup) inserts the 5 README-fixed `metodos_pago` rows if missing — this used to not exist at all ("an empty DB has zero `metodos_pago` rows despite the README's fixed set" was previously true; it no longer is). `reglas_cobro` is deliberately **not** seeded — billing rules are club-defined config the admin enters via Ajustes, not a fixed set from the README.
- **Feature folders**: each domain screen should live under `features/<domain>/` with its view, toolbar, dialog(s), and services together — see `features/members/` and `features/settings/` (which further splits into one `<section>_service.py`/`<section>_dialog.py`/`<section>_toolbar.py`/`<section>_view.py` file set per hub section, since it hosts multiple sub-screens under one `menu_view.py` hub rather than a single screen). Only genuinely cross-cutting code (ORM models, `common/view_registry.py`'s generic table browsing — currently unused by any screen, see its note above — app shell/menu bar in `ui/`, logging, `database/audit.py`, `database/seed_db.py`, `utils/text.py`) belongs outside a feature folder.
- **Table → screen mapping (post-"Vistas")**: since the generic multi-table browser was retired from Members, each DB table's UI home is a deliberate per-table decision, not "whatever `ViewRegistry` happens to expose": `socios` → Members (done); `metodos_pago`/`reglas_cobro` → the Settings hub, as small grids (done — see `features/settings/`); `transacciones` → the future Transacciones screen; `periodo` → the future Periods screen; `saldos_socios` → never a raw table view — surfaces only as a derived per-socio balance display inside Members/Reports; `logs` → still an **open decision** (candidate: a tab under Settings, or a small `features/audit/` screen; a readable timeline/text view — "05/01 14:32 — Sergio editó al socio #1002: teléfono cambiado de X a Y" — fits its narrative-shaped rows better than a raw grid). `logs` is the one table left without an assigned screen. Follow this mapping when building transactions/periods/reports rather than reaching for a generic table browser.
- **Dialogs/forms**: `features/members/dialog.py` (`MemberDialog`), `features/settings/metodos_pago_dialog.py` (`MetodoPagoDialog`) and `features/settings/reglas_cobro_dialog.py` (`ReglaCobroDialog`) all follow the same one-class-handles-create-and-edit shape (`initial_data`/`initial_nombre` switches to edit mode). There is still no transaction-registration dialog — that toolbar action (`MembersToolBar.on_register_movements` / "Registrar") remains an intentionally inert placeholder.
