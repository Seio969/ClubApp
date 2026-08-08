# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Desktop management app ("Club Social Paraiso") for a club's members and finances: member records, dues/payments/refunds, per-period balances, and reporting. Built with **PySide6** (Qt) for the UI, **SQLAlchemy** ORM over **SQLite** for persistence. Domain/UI text and identifiers are in Spanish (Socio = member, Transaccion = transaction, Periodo = period, etc.) — match this convention when adding new domain code.

The app is early-stage: most CRUD actions are logging placeholders (see per-file notes below), and only the "Gestionar Miembros" (members) screen is wired up from the main menu.

See [README.md](README.md) for the full functional/non-functional requirements spec (in Spanish) and [db.md](db.md) for a mermaid ER diagram of the *intended* schema (note: it has drifted from the actual code — see "Schema drift" below).

## Commands

Dependencies are managed with **uv** (`uv.lock` is present; no `requirements.txt`, no `pip`).

- Install deps: `uv sync`
- Run the app (from repo root): `uv run python src/main.py`
- Initialize/reset the DB schema only: `uv run python src/database/init_db.py` (calls `Base.metadata.create_all` — creates missing tables, does **not** drop/alter existing ones, so it won't pick up column changes on an existing `data/club_manager.db`; delete the DB file to fully rebuild)

There is no test suite, linter, formatter, or type-checker configured anywhere in this repo (no `pytest`, `ruff`, `mypy`, etc. in `pyproject.toml`).

### Import path convention

Every module uses absolute imports rooted at `src/` (e.g. `from database.session import engine`, `from features.members.menu_view import show_members_view`, `from utils.logger import get_logger`) — never `from src....`. This only resolves when `src/` itself is on `sys.path`, which happens automatically because Python prepends the running script's own directory. In practice this means:
- Always run/debug via `src/main.py` as the entry script (`uv run python src/main.py` from repo root works because `src/` becomes `sys.path[0]`).
- Don't invoke it as `python -m src.main` or import `src` as a package — the internal imports will fail.
- If running an individual module directly for a quick check (e.g. `python src/database/init_db.py`), that also works for the same reason (its own dir's parent isn't added, but `src/` is `sys.path[0]` since the script lives there).

## Directory layout and file-by-file reference

The codebase is organized as a hybrid: `database/`/`common/`/`ui/`/`utils/` are cross-cutting layers (ORM models, generic table browsing, app shell/chrome, logging), while each domain screen lives in its own package under `features/` (view, toolbar, dialog, and backing services together). As new domains (transactions, periods, reports) get built out, they should each get their own `features/<domain>/` package following the `features/members/` shape below, rather than adding more flat files to a `services/` layer.

```
src/
  config.py                 # paths + DB URL
  main.py                   # entry point
  database/
    models.py                # SQLAlchemy ORM models (source of truth for schema)
    session.py                # engine + SessionLocal + get_session() context manager
    init_db.py                # creates tables from models
    db.sql                    # STALE schema dump, see "Schema drift"
  common/
    view_registry.py          # generic table/view discovery + fetch (not feature-specific)
  features/
    members/
      menu_service.py          # search + view-loading logic for the members screen
      toolbar_service.py       # CRUD-ish logic for the members toolbar
      menu_view.py              # the members screen (search bar, views dropdown, table)
      toolbar.py                 # QToolBar with Nuevo/Editar/Eliminar/Refrescar/Exportar/Registrar
      dialog.py                   # add/edit member dialog
      column_fill.py               # table column-width-fill helper
      table_sort.py                 # 3-state header-click sort mixin
  ui/
    styles.py                  # shared QSS stylesheet strings
    main_window.py              # QMainWindow + QStackedWidget shell
    views/
      main_menu_widget.py        # home screen
      menu_bar.py                 # QMenuBar (File/Edit/View/Help)
  utils/
    logger.py                  # rotating file + stdout logger factory
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
| `MetodoPago` | `metodos_pago` | `id_metodo` | `nombre` (unique) | `transacciones` |
| `Periodo` | `periodo` | `id_periodo` | `nombre`, `fecha_inicio`, `fecha_fin`, `estado` (default `"abierto"`) | `transacciones`, `saldos` |
| `ReglaCobro` | `reglas_cobro` | `id_regla` | `descripcion`, `cuota_mensual`, `plazo_pago`, `penalizacion`, `descuento` | none (standalone config table; nothing FKs into it yet) |
| `Transaccion` | `transacciones` | `id_transaccion` | `numero_socio` (FK → `socios.numero_socio`), `id_periodo` (FK), `id_metodo` (FK), `tipo` (cargo/pago/reembolso), `monto`, `fecha` (default `date.today`), `referencia` | `socio`, `periodo`, `metodo` |
| `SaldoSocios` | `saldos_socios` | `id_saldo` | `numero_socio` (FK), `id_periodo` (FK), `saldo_anterior`, `cargos`, `pagos`, `saldo_actual` (all default `0`); `UniqueConstraint(numero_socio, id_periodo)` — one balance row per member-family per period | `socio`, `periodo` |
| `Log` | `logs` | `id_log` | `id_socio` (FK → `socios.id_socio`, **not** `numero_socio`), `accion`, `tabla_afectada`, `id_registro_afectado`, `descripcion_cambio`, `fecha_hora` (default `datetime.now`) | `socio` |

**Important nuance (explicitly called out in a code comment on `Socio.numero_socio`):** `numero_socio` is a shared family/household identifier and is **not unique per `Socio` row** — multiple family members can share one `numero_socio`. `Transaccion` and `SaldoSocios` intentionally FK against `numero_socio` (the family), not `id_socio` (the individual). `Log`, by contrast, FKs against `id_socio` (the individual). Don't "fix" this by making `numero_socio` unique or by switching `Transaccion`/`SaldoSocios` to FK on `id_socio` — it's deliberate.

No Alembic/migration tooling exists — schema changes are made directly in `models.py` and applied via `create_all` (additive only) or by deleting `data/club_manager.db` and re-running `init_db()`.

### `src/database/session.py`
`echo` is no longer hardcoded — it reads `_ECHO = os.environ.get("CLUBAPP_DB_ECHO", ...)`, so verbose SQL logging is opt-in (`CLUBAPP_DB_ECHO=1`) instead of always-on. A `connect` event listener sets `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` on every new connection so reads (the table/view browser) aren't blocked behind an in-progress write; it deliberately does **not** set `PRAGMA foreign_keys=ON` (see the docstring — enabling it makes SQLite reject the intentional non-unique `numero_socio` FK relationship). `SessionLocal` (the raw sessionmaker) is still exported, but the preferred way to write is the `get_session()` context manager defined here: it yields a `Session`, commits on success, rolls back and re-raises on exception, and always closes — `MembersService.add_member` and `MembersService.delete_members` (`features/members/toolbar_service.py`) are its callers so far. `view_registry.py` still talks to the DB via raw `engine.connect()` + `text()`, not the ORM session.

### `src/database/init_db.py`
Just `Base.metadata.create_all(bind=engine)` plus a log line. No seed data is inserted (e.g. `metodos_pago` rows for REMESA/EFECTIVO/TRANSFERENCIA/etc. from the README are not created anywhere in code).

### `src/database/db.sql` and `db.md` — Schema drift (read before trusting either)
Both are **manually-maintained reference dumps that no longer match `models.py`**, and neither is generated from the ORM. Concretely:
- `db.sql`'s `socios` table has a `forma_pago VARCHAR` column with `FOREIGN KEY(forma_pago) REFERENCES metodos_pago (id_metodo)` — this column **does not exist** on `Socio` in `models.py`.
- `db.sql`'s `transacciones` table has an `estado VARCHAR` column — **not present** on `Transaccion` in `models.py`.
- `db.md`'s mermaid diagram uses `id_usuario`/`usuarios` naming instead of the actual `id_socio`/`socios` used in code, and lists fields (e.g. `saldos_usuarios.id_saldo`) that only loosely match the real `saldos_socios` table.
- Treat `models.py` as the single source of truth. If you update the schema, consider updating `db.sql`/`db.md` too for documentation purposes, but do not derive code from them.

### `src/common/view_registry.py` — `ViewRegistry`
Central mechanism for generic, DB-driven table browsing:
- `__init__` calls `get_db_tables()` (via `sqlalchemy.inspect(engine).get_table_names()`) and auto-registers every table as a `"table"`-type view via `register_table_view` (swallows exceptions so a broken inspector doesn't crash construction).
- Also supports `register_sql_view(name, sql, description)` (arbitrary `SELECT`) and `register_callable_view(name, func, description)` (a zero-arg callable returning `(keys, rows)`) for future non-table-backed views — neither is currently used by any call site, but the plumbing exists.
- `fetch_table(table_name, limit)`: validates the table exists, builds `SELECT * FROM "<table>"` (optionally `LIMIT :limit` via a bound parameter — safe from injection for the limit value), executes via a raw `engine.connect()`, returns `(keys, rows)`. `limit=0` is normalized to "no limit" (`None`).
- `fetch_view(name, limit)`: dispatches on the registered type (`table`/`sql`/`callable`); for `sql`-type views it tries `f"{sql} LIMIT :limit"` first and falls back to the raw unlimited SQL if that fails (e.g. if the SQL already has a trailing clause `LIMIT` can't just be appended to). **Caution**: `table_name`/`sql` values are interpolated directly into the query string via an f-string (not parameterized) — safe today because table names only ever come from `inspector.get_table_names()`, not user input, but don't extend this to accept arbitrary user-supplied table/SQL strings without adding validation.
- All methods catch broad `Exception`, log via `logger.exception(...)`, and return empty results rather than raising — callers never need to handle exceptions from this class, but failures are silent unless you check the logs.

### `src/features/members/menu_service.py` — `MembersMenuService`
- `__init__` owns one `ViewRegistry` instance.
- `search_members(text, model, limit)`: **placeholder/demo implementation** — it does not query the database at all. It clears the model, and if `text` is non-empty, appends exactly one fabricated row `["1", text, "n/a@example.com", "Activo"]`. Marked `# FIXME: Replace with real DB query logic` in the source. Don't assume search is functional.
- `get_db_tables()` / `get_views()`: thin passthroughs to `ViewRegistry`.
- `fetch_view(name, model, limit)`: the real data-loading path used by the "Vistas" dropdown. Calls `ViewRegistry.fetch_view`, then rebuilds the `QStandardItemModel` in place — clears rows, sets column count/headers from the returned `keys`, and appends one `QStandardItem` row per DB row (`None` → empty string item). Returns row count.
- `fetch_table(...)`: kept only for backward compatibility, delegates to `fetch_view`.
- `get_filter_labels(model)`: reads header text off each column of a Qt model (used to populate the "Filtros" show/hide-column menu) — pure UI-data extraction, tolerant of `None` headers.

### `src/features/members/toolbar_service.py` — `MembersService`
UI-decoupled backend for the members toolbar. Most methods are still logging placeholders; `add_member` now persists (see below):
- `add_member(data)`: creates a `Socio` row via `database.session.get_session()` and returns its new `id_socio`, or `None` on failure.
- `edit_member(selected_indices, model_getter)`: if a row is selected, best-effort reads column-0's value via the provided `model_getter` callback and logs it; otherwise logs a warning. No edit dialog or persistence.
- `delete_members(selected_indices, model_getter)`: **soft-delete only, never a physical `DELETE`** — for each selected row it reads column-0 (`id_socio`) via `model_getter`, then updates that `Socio.estado = "inactivo"` via `get_session()`. **Decided (durable):** "Eliminar" in the members toolbar always means deactivation via `UPDATE estado = "inactivo"`, so transaction/balance/log history referencing the member is preserved — a physical `DELETE FROM socios` path is not planned. Returns the row indices (deduped, sorted descending) that were successfully deactivated; `MembersToolBar.on_delete_member` then calls `model.removeRow(r)` on those for immediate UI feedback. Since nothing filters by `estado` yet, a deactivated member still reappears (now correctly marked `estado="inactivo"`) the next time the view is reloaded — a confirmation dialog before this action and estado-aware filtering/display are still unbuilt.
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
Three `Final[str]` constants: `MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET` (Qt QSS strings), plus two small inline-style snippets `TITLE_STYLE`/`BUTTON_FONT_STYLE`. `MEMBERS_MENU_STYLESHEET` includes a `#resultsTable QHeaderView::section { color: #000000; }` rule so header text stays black. Remember QSS only supports `/* ... */` comments — a `#`-prefixed "comment" is silently parsed as a malformed ID-selector block instead of being ignored, which is how a prior version of this rule went dead without erroring.

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
- `"⚙️ Ajustes"` → wired to a no-op that just logs the click (settings screen doesn't exist yet).
Button wiring is done by matching on the button's emoji prefix (`button.startswith("🧑‍🤝‍🧑")` / `startswith("⚙️")`) inside the loop that creates them — if you add a new home-menu button, follow this same emoji-prefix-dispatch pattern or refactor it, but be aware this is how routing currently works here.
Also defines `show_home()`, a convenience to switch the stack back to itself — but nothing currently calls it (back-navigation is instead handled by `MembersMenuView.on_back_to_main_menu`, which reaches into `main_window._stack`/`main_window._home` directly).

### `src/features/members/menu_view.py` — `MembersMenuView(QWidget)`
The largest and most complex file in the codebase. Layout, top to bottom:
1. **Top bar** (`#topBar`): left = "Volver" back button (`on_back_to_main_menu`, switches the stack to `main_window._home`); center = search `QLineEdit` (`self.search_input`, placeholder "Buscar miembros, email, id...") + "Buscar" button, both wired to `on_search`; middle = a "Límite:" numeric `QLineEdit` (`self.limit_input`, `QIntValidator(0, 99999)`, default text `"0"`, Enter triggers `on_limit_changed`); right = two `QToolButton`s with popup menus — "Vistas" (`self.views_menu`, populated by `_populate_db_views()` from `MembersMenuService.get_views()`) and "Filtros" (`self.filters_menu`, checkable per-column show/hide actions built by `_populate_filters_menu()`).
2. **Toolbar**: a `MembersToolBar` instance (see below), given references to the table/model via `set_table_references`.
3. **Central area**: a `QTableView` (`self.table`) backed by a `QStandardItemModel` (`self.model`, starts as 0 rows × 4 cols). Header uses `Interactive` resize mode (user-draggable) with `setDefaultSectionSize(120)`; sorting and moving of sections are enabled manually rather than via Qt's built-in sort-on-click.

Key behaviors:
- **Auto-load on construction**: after wiring everything up, it calls `self._service.get_views()` and tries to auto-select a view named `"socios"` (case-insensitive; marked with a `# TODO: move to settings/config`), falling back to the first available view, and loads it via `load_table_view`.
- **`get_limit()`**: parses `limit_input` text; empty/`0`/parse-error all mean "no limit" (`None`); otherwise clamps to `[1, 99999]`.
- **`on_search()`**: delegates to `MembersMenuService.search_members` (remember: currently a demo/placeholder, see above) and remembers `self._last_search_text` for later sort-clearing restoration.
- **`load_table_view(table_name)`**: the real DB-load path — sets `self._current_view_name`, calls `MembersMenuService.fetch_view`, repopulates the filters menu, re-applies any active sort (`_maybe_reapply_sort`), and re-runs `ensure_columns_fill()`.
- **`refresh_table()`**: re-invokes `load_table_view` for `self._current_view_name` if set, else loads the first available view. This is what `MembersToolBar`'s "Refrescar" action calls via duck-typing (`hasattr(parent, "refresh_table")`).
- **Custom column-fill logic (`ensure_columns_fill`)**: rather than Qt's `Stretch` resize mode (which disables interactive resizing), this manually distributes any leftover viewport width proportionally across visible columns on each resize (hooked via an `eventFilter` on `self.table.viewport()`, listening for `QEvent.Type.Resize`) — chosen specifically to keep columns both interactively resizable *and* filling available width. If you touch table sizing, understand this custom mechanism before reaching for `QHeaderView.ResizeMode.Stretch`.
- **Custom 3-state sort (`_on_header_clicked` → `_apply_sort`/`_clear_sort`)**: clicking a header cycles ascending → descending → unsorted (not Qt's built-in `sortByColumn`). Sorting is done in Python by reading every cell's text out of the model, sorting the plain rows, and rebuilding the model from scratch (`_make_sort_key` prefers numeric comparison when a cell parses as int/float, else falls back to `_normalize_for_sort`, which strips accents via `unicodedata` NFKD normalization and casefolds — so "Álvaro" sorts next to "Alvaro"). Clearing sort restores data by re-running `load_table_view` (if a DB view is active) or re-running the last search (if not), rather than keeping a cached "original order" — so a slow/failing DB fetch will also slow down/break "un-sorting".
- **`show_members_view(main_window)`** (module-level function): the singleton-view navigation helper described in the architecture section — creates one `MembersMenuView` cached as `main_window._members_view`, adds it to `main_window._stack` once, and calls `setCurrentWidget` on every call thereafter.
- Several handlers wrap logic in bare `try/except Exception: pass` (e.g. the auto-load-view block, `ensure_columns_fill()` calls) — failures here are silently swallowed with no log line, unlike most of the rest of the codebase which logs exceptions. Be aware when debugging that some errors in this file produce no trace at all.

### `src/features/members/toolbar.py` — `MembersToolBar(QToolBar)`
Non-movable toolbar, 18×18 icons, actions built from Qt's built-in `QStyle.SP_*` standard icons (no custom icon assets in the repo): Nuevo (`SP_FileIcon`) → `on_add_member`; Editar (`SP_DialogApplyButton`) → `on_edit_member`; Eliminar (`SP_TrashIcon`) → `on_delete_member`; separator; Refrescar (`SP_BrowserReload`) → `on_refresh`; Exportar (`SP_DialogSaveButton`) → `on_export`; Registrar (`SP_DialogOpenButton`) → `on_register_movements`. Takes an optional `MembersService` (defaults to constructing its own). `set_table_references(table, model)` is called by the parent view right after construction so the toolbar can read selection/model state without owning it.
- `on_edit_member`: reads selected row indices from `self.table.selectionModel().selectedRows()`, delegates to `MembersService.edit_member` — no persistence yet (see that method's notes above).
- `on_delete_member`: reads selected row indices, passes them plus a `model_getter` closure to `MembersService.delete_members` (so the service can resolve each row's `id_socio`), then calls `self.model.removeRow(r)` for each row index the service confirms was deactivated in the DB.
- `on_refresh`: prefers `parent.refresh_table()` when the parent view exposes one; otherwise logs and no-ops (deliberately does not fall back to inserting demo/sample rows).
- `on_export`: flattens the current model into `list[list[str]]` (missing items become `""`) and passes to `MembersService.export_members` — currently a no-op logger call.

## Cross-cutting notes

- **Encoding/locale**: sorting/searching normalizes Spanish diacritics (see `_normalize_for_sort` above) — keep this in mind for any new text-comparison code so accented names keep sorting correctly.
- **Error handling style**: most services/UI code catches broad `Exception`, logs via `logger.exception(...)`/`logger.warning(...)`, and returns a safe empty/default value rather than propagating — match this style for consistency, but note the `menu_view.py` exceptions to it called out above.
- **No seed/demo data loader**: an empty `data/club_manager.db` will have all tables but zero rows (including `metodos_pago`, despite the fixed set of payment methods described in the README) — inserting reference data is not yet automated anywhere.
- **Feature folders**: each domain screen (members today; transactions/periods/reports eventually) should live under `features/<domain>/` with its view, toolbar, dialog(s), and services together — see the `features/members/` package. Only genuinely cross-cutting code (ORM models, generic table browsing in `common/view_registry.py`, app shell/menu bar in `ui/`, logging) belongs outside a feature folder.
- **Dialogs/forms**: `features/members/dialog.py` (`MemberDialog`) now exists for adding a member; there is still no edit-member dialog, transaction-registration dialog, or settings screen — those toolbar/menu actions remain intentionally inert placeholders.
