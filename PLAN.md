# ClubApp — Current state and pending work plan

_Generated: 2026-08-08. Based on direct inspection of the code in `src/`, `README.md`, `db.md`, `pyproject.toml`, and `CLAUDE.md`._

## 0. Executive summary

The project is at a **very early stage**: the "Gestionar Miembros" (Manage Members) screen and a "⚙️ Ajustes" (Settings) hub are wired up. Within Members, member CRUD (search/create/edit/deactivate) is fully implemented, persisted, and audit-logged — export and transaction-registration are still logging placeholders. Within Ajustes, payment methods and billing rules both have full CRUD (soft-deactivation only, same pattern as members), and a database reset action (full wipe + scoped reset, type-to-confirm safety flow) exists. The rest of the financial functionality described in `README.md` (transactions, balances, periods, reports, backups, import) **has no UI or service implemented at all**, even though the ORM schema for almost everything already exists in `models.py`. There is a `pytest` suite (see §3) but no linter, no type-checker, and no CI configured.

This document lists, by category, everything that's pending and proposes an execution order.

---

## 1. Known bugs to fix first

**Completed** (branch `fix/quick-bugs-plan-section-1`):
- [x] `on_refresh` indentation fixed
- [x] Dead QSS header-color comment fixed
- [x] `main.py` DB-path check now uses `config.DATA_DIR`
- [x] `delete_members` now soft-deletes via DB `UPDATE`

**Still pending — new request (user-observed, not yet implemented):**
- **Multi-select "Editar" silently edits only the first selected row.** Affects all three toolbars that have an edit action: `MembersToolBar.on_edit_member`, `MetodosPagoToolBar.on_edit_metodo`, `ReglasCobroToolBar.on_edit_regla` — each resolves the target row via `sel[0]`/`_selected_row()` without checking how many rows are selected, so selecting several and clicking "Editar" quietly opens the dialog for just the first one. **Decided (durable):** edit should instead refuse (info message, no dialog) whenever more than one row is selected — editing stays strictly single-row across all three toolbars.
- **Batch activar/desactivar for métodos de pago and reglas de cobro.** Unlike edit, status changes should support acting on multiple selected rows at once — contrasted deliberately with the edit restriction above. Members' "Eliminar" (`MembersService.delete_members`) already supports this (batch deactivate, one confirmation for the whole selection); `MetodosPagoToolBar`/`ReglasCobroToolBar`'s "Activar/Desactivar" currently only reads a single selected row (`_selected_row()`) and flips whatever that one row's current `estado` is. **Open design question to resolve before implementing:** a single toggle button is ambiguous once multiple rows with *mixed* current states (some activo, some inactivo) are selected — candidate approach: split "Activar/Desactivar" into two separate, always-batch-capable buttons ("Activar" / "Desactivar"), mirroring `delete_members`'s existing batch shape (list of row indices, one confirmation, per-row service call) instead of one ambiguous toggle.

---

## 2. Critical business functionality — not implemented

**Completed** (branch `feat/members-crud-completion`):
- [x] Real member search & default table load — replaced the `# FIXME` placeholder with a real query over `socios`; the default load now goes through the same query path instead of `ViewRegistry` (2.3)
- [x] Editing members — `MemberDialog` reused in an "edit" mode (`initial_data`) + `MembersService.get_member`/`update_member` (2.1)
- [x] Deactivation confirmation dialog before `MembersToolBar.on_delete_member` fires (2.2 / 4.3)
- [x] Audit log rows written on every member create/edit/deactivate, via `database/audit.py`'s `record_log` (2.12 — writing only; reading them back is still open, see 2.12 below)
- [x] Retired the generic "Vistas" multi-table browser from the Members screen (2.16)

**Completed** (branch `feat/seed-data-and-settings`):
- [x] `metodos_pago` seeded with the 5 fixed README methods, idempotent, run from `init_db()` (2.7 / 3.5)
- [x] Settings screen implemented as a real hub (`⚙️ Ajustes`) with section navigation, replacing the no-op button (2.7)
- [x] Payment methods (`MetodoPago`) full CRUD — fixed methods protected from rename/delete but deactivatable, custom methods fully editable, soft-deactivation only (2.7)
- [x] Billing rules (`ReglaCobro`) full CRUD — multiple named rules supported, soft-deactivation only (2.7)
- [x] Database reset action — full wipe + scoped reset, type-to-confirm safety flow (2.15)

Everything below already has an ORM model declared in `models.py` but **zero UI and zero service logic**, except where noted above:

### 2.2 Deactivating members (not physical deletion)
- Deactivation and its confirmation dialog are both done (see Completed block above).
- **Still pending**: estado-aware filtering/display — today a deactivated member still shows up (now correctly marked `inactivo`) on the next reload since nothing filters by `estado` yet.

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
- Writing `Log` rows on every member create/edit/deactivate is done (see Completed block above).
- **Still pending (separate from writing logs):** where a user actually *reads* them back — no audit-log viewer screen exists yet. A readable timeline/text view fits `logs`' narrative-shaped rows (`accion`, `descripcion_cambio`, `fecha_hora`) better than a raw grid — candidate location: a tab under Settings, or a small dedicated `features/audit/` screen. See `CLAUDE.md`'s table-to-screen mapping note — `logs` is the one table still left without an assigned screen.

### 2.13 Security — encryption of sensitive data
- An explicit non-functional requirement in the README ("Encrypted storage of sensitive data"). The SQLite `.db` today has no encryption at all (no SQLCipher, no column-level encryption). No related dependency in `pyproject.toml`.
- **Decided**: long-term goal, not scheduled work yet. Revisit once the functional domain (transactions, balances, reports) is mature and there's real club data to protect.

### 2.14 SQLite → PostgreSQL migration (scalability)
- Non-functional requirement; today `DATABASE_URL` is hardcoded to SQLite in `config.py` and there's no Alembic or any schema-migration layer — only additive `create_all`. Introducing Alembic would be a reasonable prerequisite before attempting the move to Postgres.
- **Decided**: long-term goal, same as 2.13 — keep using `create_all`/SQLite for now; no Alembic work scheduled yet.

### 2.15b Legacy Excel (`.xlsm`) analysis — source of truth this app is replacing
- **New request.** The club currently runs this process out of a hand-built `.xlsm` workbook; this repo is meant to **replace** it. The file has not been attached to the repo yet — this item tracks the analysis step for when it is.
- **Scope of the analysis, once the file is attached:**
  1. Unzip the `.xlsm` (it's a zip container, same as `.xlsx` plus a macro part) and read `xl/worksheets/*.xml`, formulas, and named ranges directly, or via `openpyxl`/`pandas`.
  2. Extract and decompile the VBA project (`xl/vbaProject.bin`, OLE/Compound-File binary — not plain-text) using `oletools`/`olevba` (add as a throwaway dev dependency or run in an isolated scratch venv; not a runtime dependency of the app itself) to get the actual macro source.
  3. Document, in plain language, what each sheet/macro computes — cuota/penalización/descuento rules, balance carry-over, any reporting/export macros — and cross-reference against `ReglaCobro`'s existing (currently orphaned, see 2.7) columns and the balance logic gap in 2.5, since this workbook is likely the actual origin of both.
  4. Produce a mapping from "what the workbook does" → "which planned feature/service it belongs to" (2.4 transactions, 2.5 balances, 2.7 billing rules/settings, 2.8 reports) before writing implementation code — this is analysis-and-mapping, not a build step itself.
- **Decided (workflow):** analyze and document first, agree on the implementation mapping, *then* implement inside the relevant `features/<domain>/` package — not a direct/blind port of VBA into Python.
- Depends on: the user attaching the `.xlsm` file (not yet done as of this entry).

---

## 3. Technical debt / infrastructure

1. **No test suite (high priority).**

   **Completed** (branch `chore/testing-infrastructure`): `pytest` added as a dev dependency with `tests/` wired up (`tests/conftest.py`'s `test_engine` fixture isolates every DB-touching test on a throwaway SQLite file), plus first tests for `MembersService.add_member`, `ViewRegistry`, and `TableSortMixin._normalize_for_sort`/`_make_sort_key` (`features/members/table_sort.py`). See `CLAUDE.md`'s `tests/` section for what's covered and the fixture's engine-patching gotcha.

   **Still pending:**
   - `pytest-qt` — deferred, no test yet needs a real `QApplication`.
   - Aggressively separating pure logic (services: `toolbar_service.py`, `menu_service.py`, future `transactions/service.py`, balance calculation) from the Qt layer beyond what's already service-separated.
   - Tests for balance calculation, once that logic exists (2.5).
   - No Qt-level tests yet (views/dialogs/toolbars) — `get_member`/`update_member`/`delete_members`/`search_members` now have service-level coverage (see `CLAUDE.md`'s `tests/` section), but nothing exercises the toolbar's confirmation dialog or dialog pre-fill through a real `QApplication`. No coverage of exports.
2. **No linter/formatter/type-checker.** No `ruff`, `black`, or `mypy` in `pyproject.toml`. Since the code already uses type hints (`Optional`, `dict[str, Any]`, etc.), `mypy` or `pyright` would add real value, especially in the service layer.
3. **No CI.** No `.github/workflows/`. Once a test suite exists, adding a minimal workflow (`uv sync` + `pytest`) would catch regressions like the `on_refresh` indentation bug — though a linter would have caught that one too (even if not as a syntax error).
4. **`db.sql` and `db.md` are out of date** relative to `models.py` (a `forma_pago`/`estado` columns in `db.sql` that don't exist on the ORM; `id_usuario`/`usuarios` naming in `db.md` that doesn't match `id_socio`/`socios`). Decide: keep them manually in sync every time `models.py` changes, or generate them automatically (e.g. with `sqlalchemy-schemadisplay` or similar) so they can't drift again.
6. **No migrations (Alembic).** Any column change today requires manually deleting the `.db`; as the schema grows (transactions, balances, etc.) this becomes risky for a club's real data. Introduce Alembic soon, before there's production data to protect.
8. **Business-standard test scenarios.** **New request** — not previously in this plan. Distinct from unit tests over individual functions (item 1 above): this is a set of named, documented scenarios that encode the club's actual business rules end-to-end, e.g. "member pays full quota on time", "member pays late → penalty from `ReglaCobro` applied", "discount rule applied correctly", "refund attempted with no prior payment → rejected" (2.4's integrity rule), "period closed → new transactions against it are rejected" (2.6), "balance carried over correctly from a closed period to the next open one" (2.5). These should live as acceptance-style tests (e.g. `tests/scenarios/`) once pytest is in place (item 1), each scenario asserting the final DB state against the business rule it documents. The user has a separate realistic fake-data generator (one level above this repo) they intend to wire into the workspace later for populating the DB with sample data for manual testing/demos — that's a different, complementary concern from these business-rule scenarios, which are about *correctness*, not data volume.

---

## 4. Pending UI / UX

1. **File/Edit menu** in `menu_bar.py` — New/Open/Save and all of Edit (Undo/Redo/Cut/Copy/Paste) are deliberate `not_implemented` stubs. Confirm with the user which of these make real sense in a desktop management app (Save/Open probably don't apply to an app backed by a persistent SQLite DB; Undo/Redo could have real value for member-editing operations).
2. **Transactions, Periods, Reports screens** — don't exist yet, not even as a skeleton (`features/transactions/`, `features/periods/`, `features/reports/` haven't been created). Only `features/members/` and `features/settings/` follow the per-domain folder pattern documented in `CLAUDE.md`. For Transacciones specifically, see 2.4's decided navigation model: a member-scoped shortcut via Members' existing "Registrar" button *and* a standalone main-menu screen, not one or the other.
3. **Overall visual/UI polish.** Bug 1.2 covers one specific rendering defect (the broken QSS header-color rule), but there's no wider design work planned yet: today the app is three hand-written QSS strings (`MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET`, `SETTINGS_MENU_STYLESHEET` in `styles.py` — the latter two already near-duplicates of each other) plus Qt's built-in `QStyle.SP_*` stock icons (no custom icon set, no consistent spacing/typography system, no light/dark theme, no design tokens). **Decided**: no specific reference given — Claude proposed a clean, modern look (palette, spacing, icons) for approval before wider rollout; see [`UI_PROPOSAL.md`](UI_PROPOSAL.md) for the full audit and design direction (token layer, unified ledger palette, `qtawesome` icons, extracted shared table/toolbar composition for future screens).

---

## 5. Recommended order of work

1. **Quick bugs** (section 1) — low effort, avoids future confusion.
2. **Minimal testing infrastructure** — `pytest` + first tests over what already exists and persists (`MembersService.add_member`, `ViewRegistry`, sort functions). This provides a safety net before touching more business logic.
3. **Complete the Members CRUD** — real search (2.3), editing (2.1), logical deactivation with confirmation (2.2, 4.3), audit logging (2.12) on every write operation, and retiring the generic "Vistas" table-switcher in favor of a proper members-only load path (2.16). This fully closes out the one partially-built domain before opening a new one.
4. **Seed data + Settings** — fixed payment methods and billing rules (2.7), since the transactions module depends on payment methods existing. Add the **database reset action** (2.15) to the same Settings screen while it's being built.
5. **Transactions module** (2.4) — the next most important functional domain and the one that delivers the most business value.
6. **Balance calculation and Periods** (2.5, 2.6) — depends on transactions existing.
7. **Business-standard test scenarios** (3.8) — once the rules they encode (2.4, 2.5, 2.6, 2.7) actually exist, write the acceptance-style scenarios that pin down correct behavior for late payments, penalties, discounts, rejected refunds, and balance carry-over.
8. **Reports + export** (2.8), then **charts/statistics** (2.9).
9. **Backups** (2.10) and **import** (2.11) — more independent features, can be tackled in parallel or at the end.
10. **Long-term non-functionals**: Alembic (a technical prerequisite — move it earlier if the schema starts changing a lot), encryption (2.13), Postgres migration (2.14) — these come into play once the functional domain is more mature and there's real data to protect.
11. **Visual/UI polish** (4.3) — best done once the screens it applies to actually exist (transactions/periods/reports), so styling isn't reworked twice; earlier if the user wants the look-and-feel decided up front instead.

---

## 6. Decisions (resolved)

All previously open questions have been answered by the user; nothing outstanding here for now.

- **Delete-member semantics**: soft delete only — "Eliminar" always sets `estado = "inactivo"`, never a physical `DELETE`. See 2.2.
- **Export format priority**: Excel first (`openpyxl`), PDF later. See 2.8.
- **Postgres migration / encryption timeline**: long-term goals, not scheduled now — keep `create_all`/SQLite until the functional domain is mature. See 2.13, 2.14.
- **UI redesign direction**: no specific reference from the user — Claude proposed a design (palette, spacing, icons) in [`UI_PROPOSAL.md`](UI_PROPOSAL.md), pending approval before wide rollout. See 4.3.
- **Transactions navigation model**: both entry points, not either/or — the Members toolbar's "Registrar" button stays as a socio-pre-filled shortcut, *and* a standalone `Transacciones` screen is added to the main menu for club-wide browsing/filtering (README's fecha/tipo/estado filter requirement needs the standalone screen; the quick shortcut alone couldn't satisfy it). Both share one dialog and one service. See 2.4.
