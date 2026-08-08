# ClubApp — Current state and pending work plan

_Generated: 2026-08-08. Based on direct inspection of the code in `src/`, `README.md`, `db.md`, `pyproject.toml`, and `CLAUDE.md`._

## 0. Executive summary

The project is at a **very early stage**: only the "Gestionar Miembros" (Manage Members) screen is partially wired up, and within it only **member creation** actually persists to the database. The rest of the financial functionality described in `README.md` (transactions, balances, periods, billing rules, reports, backups, import) **has no UI or service implemented at all**, even though the ORM schema for almost everything already exists in `models.py`. There is no test suite, no linter, no type-checker, and no CI configured.

This document lists, by category, everything that's pending and proposes an execution order.

---

## 1. Known bugs to fix first

Fix these before building more on top, since they're cheap to fix and avoid confusion when debugging new features.

1. **`src/features/members/toolbar.py::on_refresh`** — broken indentation: the final `logger.info(...)` sits at class level, not method level. It runs exactly once, at module import time, instead of every time "Refrescar" (Refresh) is clicked with no `refresh_table` available. It's valid Python (doesn't fail), but it silences the expected log line. **Fix**: re-indent that line to 8 spaces, inside the method.
2. **`src/ui/styles.py::MEMBERS_MENU_STYLESHEET`** — a "comment" block using Python-style `#` inside a QSS block (which doesn't support `#...` line comments, only `/* ... */`). This leaves a malformed CSS rule with a dangling `}`; the table header text color is never applied. **Fix**: convert it to a real `/* ... */` comment or to a proper `#resultsTable QHeaderView::section { color: #000000; }` rule.
3. **`src/main.py`** — uses `Path("data/club_manager.db")` (relative to the process's cwd) to decide whether to call `init_db()`, while `config.py`/`session.py` use an absolute (`BASE_DIR`-relative) path. If the app is ever launched from a directory other than the repo root, this check can get out of sync with the real DB. **Fix**: reuse `config.DATA_DIR` instead of a fresh relative `Path`.
4. **Deactivating members "without deleting history" (README requirement)** — `delete_members` in `toolbar_service.py` currently doesn't touch the database at all, only the in-memory table row (the record reappears on reload). It doesn't even implement the soft-delete (`estado = "inactivo"`) the README asks for; today there is no real path to deactivate a member.

---

## 2. Critical business functionality — not implemented

Everything below already has an ORM model declared in `models.py` but **zero UI and zero service logic**:

### 2.1 Editing members
- No edit dialog exists (`dialog.py` only covers creation). `MembersService.edit_member` just logs the value of column 0 of the selected row; nothing is persisted.
- **Pending**: `EditMemberDialog` (can reuse/generalize `MemberDialog` with a pre-populated "edit" mode) + `MembersService.update_member(id_socio, data)` using `get_session()`.

### 2.2 Deactivating members (not physical deletion)
- The README asks for deactivation without losing history. `estado = "inactivo"` via UPDATE (not `DELETE FROM socios`) still needs implementing, respecting the relationships (`transacciones`, `saldos`, `logs`).
- **Decided**: "Eliminar" (Delete) in the toolbar becomes soft-delete only — always `estado = "inactivo"` via UPDATE, never a physical `DELETE`. No separate physical-delete path is planned.

### 2.3 Real member search & data loading
- `MembersMenuService.search_members` is a placeholder marked `# FIXME` that fabricates a fake row (`["1", text, "n/a@example.com", "Activo"]`) — it doesn't query the DB at all.
- **Pending**: replace it with a real query (ORM or parameterized SQL) over `socios` filtering by name, surname, member number, email, with `LIKE`/accent normalization consistent with `_normalize_for_sort` in `menu_view.py`.
- The *default* table load has the same problem one level up: today it goes through `ViewRegistry.fetch_view("socios")` — a generic `SELECT * FROM socios`, not a members-owned query. Once real search exists, the default load should go through the same `MembersService` query path (e.g. "no filter" = same query with an empty filter), not through `ViewRegistry`. See 2.16 for why `ViewRegistry`-backed loading is being retired from this screen entirely.

### 2.4 Transactions module (charges / payments / refunds)
No `features/transactions/` exists yet.

**Decided — navigation model (both entry points, not either/or):**
- **Member-scoped shortcut**: the existing "Registrar" button in the Members toolbar (`on_register_movements`, currently a no-op logging the selected indices) opens the transaction dialog with the socio **pre-filled/locked** from the row(s) selected in the Members table. This is the fast path for "this member just paid."
- **Standalone screen**: a new `Transacciones` entry on the main menu, its own `features/transactions/` package (view/toolbar/dialog/service, same shape as `features/members/`), for club-wide browsing/filtering by fecha, tipo, or estado — this is the README's "Filtrar transacciones por fecha, tipo o estado" requirement (2.5 in Requisitos Funcionales), which a member-scoped-only flow can't satisfy. Reuses the shared top-bar/toolbar/table composition proposed in `UI_PROPOSAL.md` §2 (Structure) / §3 (mockups) rather than being built from scratch.
- Both entry points share **one** `TransactionDialog` and **one** `TransactionsService` — the Members-toolbar path just pre-populates the socio field and skips the picker; nothing about validation/persistence differs between the two.

**Build steps:**
1. Scaffold `features/transactions/` (view, toolbar, dialog, service) mirroring `features/members/`'s structure.
2. `TransactionDialog`: socio picker (search/select — locked/pre-filled when opened from Members' "Registrar"), tipo (cargo/pago/reembolso), monto, método de pago (dropdown sourced from `metodos_pago`, see 2.7), periodo selector (`periodo` table), referencia.
3. `TransactionsService.add_transaction(...)` via `get_session()`, following the pattern already used in `MembersService.add_member`.
4. Integrity validation: prevent a refund without a prior payment, prevent duplicate transactions (README "Data Integrity" requirement) — enforced in the service, so both entry points get it automatically.
5. Wire the Members toolbar's `on_register_movements` to open `TransactionDialog` pre-filled with the selected row's `numero_socio`, instead of logging indices.
6. Add the `Transacciones` main-menu button + screen: shared top-bar/toolbar/table composition, default-filtered to the currently open período, with fecha/tipo/estado filters.
7. Trigger balance recalculation (2.5) after a successful save from either entry point.

### 2.5 Balance calculation and carry-over (`SaldoSocios`)
- There's no service that computes `saldo_actual` from `saldo_anterior + cargos - pagos` (or similar), nor one that carries a balance from one period to the next when periods are closed/opened.
- This calculation should be triggered automatically after every transaction (README requirement "Automatic balance calculation"), most likely as part of the `Transaccion` save logic, not as a manual step.

### 2.6 Period management (`Periodo`)
- No screen to open/close/edit accounting periods. `estado` (open/closed) exists on the model but nothing changes it.
- No logic preventing transactions from being registered against a closed period.

### 2.7 Billing rules (`ReglaCobro`) and payment methods (`MetodoPago`)
- `ReglaCobro` (monthly fee, payment deadline, penalty, discount) has NO UI entry point and no read/write path from code at all — an orphaned table today.
- `metodos_pago` has no seed data anywhere (`init_db.py` only creates tables). The README defines 5 fixed payment methods (REMESA, EFECTIVO, TRANSFERENCIA, TRANSFERENCIA/EFECTIVO, INACTIVO) that should be inserted as a seeding step.
- **Pending**: a "Settings" screen (Ajustes — today a no-op button in `main_menu_widget.py`) for CRUD on billing rules and payment methods, plus a seed-data script/step.

### 2.8 Reports
- Nothing implemented: no annual per-member summary, no overall financial view, no Excel/PDF export.
- `utils/exporters.py` is **completely empty (0 bytes)**. No `openpyxl`/`reportlab` (or equivalents) in `pyproject.toml`.
- The "Exportar" button on the members toolbar already calls `MembersService.export_members`, but it only logs; it's the natural entry point to wire up a real exporter once `utils/exporters.py` exists.
- **Decided**: build Excel export first (`openpyxl`), PDF later.

### 2.9 Charts / statistics dashboard
- No charting library in dependencies (no `matplotlib`, no `pyqtgraph`, no QtCharts enabled). No screen exists.

### 2.10 Backups
- No automatic/manual backup mechanism, no restore. Nothing in the code touches this yet.

### 2.11 Drag-and-drop import from spreadsheets
- A non-functional requirement from the README; there's no Excel/CSV parser or drag-and-drop support in the current UI.

### 2.12 Audit / Log
- The `Log` model exists but **nothing in the code creates `Log` rows** yet. Not even `add_member` (the only real write operation today) records an audit log. This contradicts the "Log every change" requirement.
- **Pending**: decide on a single point (e.g. inside `get_session()` or in each write service) that inserts a `Log` row for every create/edit/deactivate.
- **Pending (separate from writing logs):** where a user actually *reads* them back. See 2.16 — removing the generic "Vistas" browser took away the one accidental way `logs` was viewable at all; a real audit-log viewer screen still needs a home before this requirement is fully satisfied.

### 2.13 Security — encryption of sensitive data
- An explicit non-functional requirement in the README ("Encrypted storage of sensitive data"). The SQLite `.db` today has no encryption at all (no SQLCipher, no column-level encryption). No related dependency in `pyproject.toml`.
- **Decided**: long-term goal, not scheduled work yet. Revisit once the functional domain (transactions, balances, reports) is mature and there's real club data to protect.

### 2.14 SQLite → PostgreSQL migration (scalability)
- Non-functional requirement; today `DATABASE_URL` is hardcoded to SQLite in `config.py` and there's no Alembic or any schema-migration layer — only additive `create_all`. Introducing Alembic would be a reasonable prerequisite before attempting the move to Postgres.
- **Decided**: long-term goal, same as 2.13 — keep using `create_all`/SQLite for now; no Alembic work scheduled yet.

### 2.15 Settings action: reset database
- **New request.** Not mentioned elsewhere in this plan and not implemented anywhere in the repo — `init_db.py` only ever calls `Base.metadata.create_all(bind=engine)`, which creates missing tables but never drops or clears existing ones (see `CLAUDE.md`'s note on this). There is currently no code path that wipes/reinitializes the database at all.
- **Decided (scope)**: support both a **full wipe** (delete `data/club_manager.db` entirely, or `drop_all` + `create_all`, then re-run seed data so `metodos_pago` etc. aren't left empty) and a **scoped reset** (clear only transactions/balances/periods while keeping members and settings intact).
- **Decided (safety)**: the user explicitly flagged this needs a *very safe* confirmation flow to avoid unintentional wipes — not a single `QMessageBox.warning` click. Use a type-to-confirm pattern (e.g. require typing the exact word "BORRAR"/"RESET" or the DB name into a text field before the action enables) plus clearly distinguishing the full-wipe button from the scoped-reset button in the UI (different color/wording) so they can't be mis-clicked for each other.
- Depends on: the Settings screen existing (2.7), seed-data script (3.5), and — since it deletes the file at `config.DATA_DIR`, not a cwd-relative path — should be built alongside the `main.py` path-consistency fix (bug 1.3) so reset and startup agree on where the DB file lives.

### 2.16 Retire the generic "Vistas" multi-table browser
- **Decided.** The Members toolbar's "Vistas" dropdown is backed by `ViewRegistry`, which auto-registers *every* table in the DB (`socios`, `metodos_pago`, `periodo`, `reglas_cobro`, `transacciones`, `saldos_socios`, `logs`) via schema introspection and dumps whichever one is picked as a raw, unformatted `SELECT * FROM <table>`. It's being removed from Members and will **not** be added to the new Transacciones screen either — it exposes internal tables (notably the audit `logs` table) to a non-technical single end user with no design intent behind which tables appear, and would show raw FK ids instead of joined/labeled data if reused for transactions.
- `ViewRegistry`/`common/view_registry.py` doesn't need to be deleted — it can stay as internal plumbing — but no production screen should call its generic `fetch_view` path going forward. Members' default load and search (2.3) move onto a real `MembersService` query instead.
- **What replaces it** — every table gets a purpose-built home instead of a generic dump, and **the table existing in the schema doesn't dictate a grid/`QTableView` presentation** — the right UI shape depends on what the data actually is, not on it being a SQL table:

  | Table | Where it becomes accessible | Presentation |
  |---|---|---|
  | `socios` | Members screen (existing) — real search/filter (2.3), not `ViewRegistry`. | Grid/table — it's a record list. |
  | `transacciones` | Transacciones screen (2.4) — filtered by fecha/tipo/estado/período. | Grid/table — same reasoning. |
  | `periodo` | Periods screen (2.6, not yet built) — open/close/edit periods. | Grid/table (small, low row count). |
  | `metodos_pago`, `reglas_cobro` | Settings screen (2.7, not yet built) — CRUD for payment methods and billing rules. | Grid/table (small, low row count). |
  | `saldos_socios` | No standalone screen — derived data (balance per socio per período). | Surfaced as a per-socio balance view inside Members and as aggregate/annual data inside Reports (2.8) — not a raw table anywhere. |
  | `logs` | **Unscoped — needs a decision**, but now with a presentation lean too. README 2.12 ("Historial de auditoría") requires this be consultable, but no screen owns it yet. Given `logs` rows are really "who did what, when" narratives (`accion`, `descripcion_cambio`, `fecha_hora`), a **readable timeline/text view** ("05/01 14:32 — Sergio editó al socio #1002: teléfono cambiado de X a Y") fits better than a grid of raw columns — candidate location: a tab under Settings, or a small dedicated `features/audit/` screen. Blocks 2.12 from being fully closed out until decided. |

---

## 3. Technical debt / infrastructure

1. **No test suite (high priority).** No `tests/` directory, no `pytest` in dependencies. Since the app mixes business logic with Qt, it's worth:
   - Aggressively separating pure logic (services: `toolbar_service.py`, `menu_service.py`, future `transactions/service.py`, balance calculation) from the Qt layer, so it's testable without spinning up a `QApplication`.
   - Adding `pytest` + `pytest-qt` (for the few cases that do need a real `QApplication`) to `pyproject.toml` as a dev dependency.
   - Prioritizing tests for: `ViewRegistry` (with an in-memory SQLite DB), `MembersService.add_member` (uses `get_session()`, easy to test with a test engine), `_normalize_for_sort`/`_make_sort_key` in `menu_view.py` (pure functions, high value, bug-prone), and eventually balance calculation (financially critical).
2. **No linter/formatter/type-checker.** No `ruff`, `black`, or `mypy` in `pyproject.toml`. Since the code already uses type hints (`Optional`, `dict[str, Any]`, etc.), `mypy` or `pyright` would add real value, especially in the service layer.
3. **No CI.** No `.github/workflows/`. Once a test suite exists, adding a minimal workflow (`uv sync` + `pytest`) would catch regressions like the `on_refresh` indentation bug — though a linter would have caught that one too (even if not as a syntax error).
4. **`db.sql` and `db.md` are out of date** relative to `models.py` (a `forma_pago`/`estado` columns in `db.sql` that don't exist on the ORM; `id_usuario`/`usuarios` naming in `db.md` that doesn't match `id_socio`/`socios`). Decide: keep them manually in sync every time `models.py` changes, or generate them automatically (e.g. with `sqlalchemy-schemadisplay` or similar) so they can't drift again.
5. **No seed-data script.** A `seed_db.py` (or an extension of `init_db.py`) is missing to insert the fixed payment methods from the README after `create_all`.
6. **No migrations (Alembic).** Any column change today requires manually deleting the `.db`; as the schema grows (transactions, balances, etc.) this becomes risky for a club's real data. Introduce Alembic soon, before there's production data to protect.
7. **`edit_member`/`delete_members` in `toolbar_service.py`** should stop being logging placeholders and start using `get_session()` the way `add_member` already does, once the edit dialog exists.
8. **Business-standard test scenarios.** **New request** — not previously in this plan. Distinct from unit tests over individual functions (item 1 above): this is a set of named, documented scenarios that encode the club's actual business rules end-to-end, e.g. "member pays full quota on time", "member pays late → penalty from `ReglaCobro` applied", "discount rule applied correctly", "refund attempted with no prior payment → rejected" (2.4's integrity rule), "period closed → new transactions against it are rejected" (2.6), "balance carried over correctly from a closed period to the next open one" (2.5). These should live as acceptance-style tests (e.g. `tests/scenarios/`) once pytest is in place (item 1), each scenario asserting the final DB state against the business rule it documents. The user has a separate realistic fake-data generator (one level above this repo) they intend to wire into the workspace later for populating the DB with sample data for manual testing/demos — that's a different, complementary concern from these business-rule scenarios, which are about *correctness*, not data volume.

---

## 4. Pending UI / UX

1. **Settings screen** (`⚙️ Ajustes` in the main menu) — currently a no-op that only logs the click. Should host: billing-rule management, payment methods, and possibly the `numero_socio`/format toggle.
2. **File/Edit menu** in `menu_bar.py` — New/Open/Save and all of Edit (Undo/Redo/Cut/Copy/Paste) are deliberate `not_implemented` stubs. Confirm with the user which of these make real sense in a desktop management app (Save/Open probably don't apply to an app backed by a persistent SQLite DB; Undo/Redo could have real value for member-editing operations).
3. **Transactions, Periods, Reports screens** — don't exist yet, not even as a skeleton (`features/transactions/`, `features/periods/`, `features/reports/` haven't been created). Only `features/members/` follows the per-domain folder pattern documented in `CLAUDE.md`. For Transacciones specifically, see 2.4's decided navigation model: a member-scoped shortcut via Members' existing "Registrar" button *and* a standalone main-menu screen, not one or the other.
4. **Confirmation before delete** — `on_delete_member` removes the model row with no confirmation dialog (`QMessageBox.question`), which is risky even while it's only in-memory today, and would be outright dangerous once it actually persists.
5. **Overall visual/UI polish.** Bug 1.2 covers one specific rendering defect (the broken QSS header-color rule), but there's no wider design work planned yet: today the app is two hand-written QSS strings (`MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET` in `styles.py`) plus Qt's built-in `QStyle.SP_*` stock icons (no custom icon set, no consistent spacing/typography system, no light/dark theme, no design tokens). **Decided**: no specific reference given — Claude proposed a clean, modern look (palette, spacing, icons) for approval before wider rollout; see [`UI_PROPOSAL.md`](UI_PROPOSAL.md) for the full audit and design direction (token layer, unified ledger palette, `qtawesome` icons, extracted shared table/toolbar composition for future screens).

---

## 5. Recommended order of work

1. **Quick bugs** (section 1) — low effort, avoids future confusion.
2. **Minimal testing infrastructure** — `pytest` + first tests over what already exists and persists (`MembersService.add_member`, `ViewRegistry`, sort functions). This provides a safety net before touching more business logic.
3. **Complete the Members CRUD** — real search (2.3), editing (2.1), logical deactivation with confirmation (2.2, 4.4), audit logging (2.12) on every write operation, and retiring the generic "Vistas" table-switcher in favor of a proper members-only load path (2.16). This fully closes out the one partially-built domain before opening a new one.
4. **Seed data + Settings** — fixed payment methods and billing rules (2.7), since the transactions module depends on payment methods existing. Add the **database reset action** (2.15) to the same Settings screen while it's being built.
5. **Transactions module** (2.4) — the next most important functional domain and the one that delivers the most business value.
6. **Balance calculation and Periods** (2.5, 2.6) — depends on transactions existing.
7. **Business-standard test scenarios** (3.8) — once the rules they encode (2.4, 2.5, 2.6, 2.7) actually exist, write the acceptance-style scenarios that pin down correct behavior for late payments, penalties, discounts, rejected refunds, and balance carry-over.
8. **Reports + export** (2.8), then **charts/statistics** (2.9).
9. **Backups** (2.10) and **import** (2.11) — more independent features, can be tackled in parallel or at the end.
10. **Long-term non-functionals**: Alembic (a technical prerequisite — move it earlier if the schema starts changing a lot), encryption (2.13), Postgres migration (2.14) — these come into play once the functional domain is more mature and there's real data to protect.
11. **Visual/UI polish** (4.5) — best done once the screens it applies to actually exist (transactions/periods/reports), so styling isn't reworked twice; earlier if the user wants the look-and-feel decided up front instead.

---

## 6. Decisions (resolved)

All previously open questions have been answered by the user; nothing outstanding here for now.

- **Delete-member semantics**: soft delete only — "Eliminar" always sets `estado = "inactivo"`, never a physical `DELETE`. See 2.2.
- **Export format priority**: Excel first (`openpyxl`), PDF later. See 2.8.
- **Postgres migration / encryption timeline**: long-term goals, not scheduled now — keep `create_all`/SQLite until the functional domain is mature. See 2.13, 2.14.
- **UI redesign direction**: no specific reference from the user — Claude proposed a design (palette, spacing, icons) in [`UI_PROPOSAL.md`](UI_PROPOSAL.md), pending approval before wide rollout. See 4.5.
- **Transactions navigation model**: both entry points, not either/or — the Members toolbar's "Registrar" button stays as a socio-pre-filled shortcut, *and* a standalone `Transacciones` screen is added to the main menu for club-wide browsing/filtering (README's fecha/tipo/estado filter requirement needs the standalone screen; the quick shortcut alone couldn't satisfy it). Both share one dialog and one service. See 2.4.
- **"Vistas" multi-table browser**: removed from Members, not added to Transacciones — it's a generic raw-table dump (including internal tables like `logs`) with no design intent, unsuitable for a non-technical end user. Each table gets a purpose-built home instead (see the mapping table in 2.16); `logs`/audit history is the one table this left without an assigned screen, still open.
- **Database reset scope**: support both a full wipe and a scoped reset (clear transactions/balances/periods, keep members/settings). Must use a very safe, type-to-confirm-style flow to prevent unintentional wipes — not a single dismissable dialog. See 2.15.
