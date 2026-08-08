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

**Completed** (branch `fix/multiselect-edit-guard`):
- [x] Multi-select "Editar" now refuses with an info message (no dialog) when more than one row is selected — `MembersToolBar.on_edit_member`, `MetodosPagoToolBar.on_edit_metodo`, `ReglasCobroToolBar.on_edit_regla`
- [x] Batch Activar/Desactivar for métodos de pago and reglas de cobro — the single ambiguous toggle is replaced by two always-batch-capable buttons

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

**Completed** (branch `feat/transactions-module`):
- [x] Transactions module (2.4) — `features/transactions/` package (service/dialog/toolbar/view), both decided entry points wired (Members "Registrar" shortcut + standalone `Transacciones` main-menu screen), integrity validation (refund-availability, exact-duplicate rejection), minimal período quick-create. See `CLAUDE.md`'s `features/transactions/` section for the full design.
- [ ] Balance recalculation (originally 2.4's build step 7) — deliberately **not** included; see 2.5 below.

**Completed** (branch `feat/titular-por-numero-socio`):
- [x] Titular (primary holder) per `numero_socio` (2.17) — `Socio.es_titular`, auto-unset-other-titular-on-swap with a UI confirmation, forced titular on a brand-new `numero_socio`, `TransactionDialog`'s picker defaulting to titulares (non-titulares within a titular-having group stay searchable), the Registrar shortcut and the open picker both fully blocked for un-migrated `numero_socio` groups until an admin assigns a titular, `cambio_titular` audit-log rows. See `CLAUDE.md`'s `features/members/` and `features/transactions/` sections.

Everything below already has an ORM model declared in `models.py` but **zero UI and zero service logic**, except where noted above:

### 2.2 Deactivating members (not physical deletion)
- Deactivation and its confirmation dialog are both done (see Completed block above).
- **Still pending**: estado-aware filtering/display — today a deactivated member still shows up (now correctly marked `inactivo`) on the next reload since nothing filters by `estado` yet.

### 2.5 Balance calculation and carry-over (`SaldoSocios`)
- There's no service that computes `saldo_actual` from `saldo_anterior + cargos - pagos` (or similar), nor one that carries a balance from one period to the next when periods are closed/opened.
- This calculation should be triggered automatically after every transaction (README requirement "Automatic balance calculation"), most likely as part of the `Transaccion` save logic, not as a manual step.
- **Decided**: intentionally not built alongside the transactions module (2.4) even though it was originally scoped as that module's last build step — the exact formula (and any carry-over/penalización/descuento nuance) is likely already defined in the legacy `.xlsm` this app is replacing (see 2.15b). Building a guessed version now risked rework once that workbook is analyzed.
- **2.15b's analysis is now done** (2026-08-08) — but it surfaced open questions rather than a ready-to-port formula: whether `saldo_actual` should be período-scoped or a continuous running total, and that legacy's "Devolución" (bounced direct debit) isn't the same concept as this app's `tipo="reembolso"` (money back to a member). Resolve those with the user before implementing this item — see 2.15b's mapping table.

### 2.6 Period management (`Periodo`)
- No screen to open/close/edit accounting periods. `estado` (open/closed) exists on the model but nothing changes it.
- No logic preventing transactions from being registered against a closed period.
- A minimal `TransactionsService.create_periodo_rapido(nombre, fecha_inicio)` now exists (added alongside 2.4) so the transaction dialog isn't blocked on this — see `CLAUDE.md`'s `features/transactions/service.py` section. It is **not** a substitute for this item: no open/close, no editing, no listing/management screen.
- **New sub-task: automatic período rollover.** Today the *only* way a new período gets created is the manual "Nuevo…" quick-create in `TransactionDialog`. **Decided (see §6):** on app-start/navigation into a screen that needs an open período (Transacciones, Members' Registrar shortcut), check whether today's date falls inside any existing período; if not, auto-create the next one (same monthly derivation as `create_periodo_rapido`: `fecha_fin` = one month minus a day after `fecha_inicio`) and auto-close whichever período was previously `abierto`, so exactly one período stays open at a time. This needs a real open/close mutation (`estado` flip) that doesn't exist yet — build that as part of this sub-task rather than waiting for the full open/close management screen.

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
**Status: analysis complete** (2026-08-08) for the member-dues workbook, `AA Control pagos SOCIOS.xlsm` (found in the user's `Downloads`, analyzed from a copy in a scratch dir — original untouched, never committed to the repo). The club actually keeps **two** separate legacy workbooks; the second one (day-to-day club accounting, not member dues) is explicitly **out of scope for this entry** — see the new 2.15c below.

Tooling: `openpyxl` + `oletools` were installed into a **throwaway `uv venv`** inside the scratch dir, not added to `pyproject.toml` — per this section's original plan, not a runtime dependency of the app.

**Workbook structure** (29 sheets):
- `ALTA (SALDO)` — master member roster (nombre, número de socio, forma de pago habitual, IBAN, observaciones) with a per-row running `SALDO` computed via `SUMIFS` over the Cargos/Pagos/Devoluciones tables **matched by name text, not by número/id** — a fragility the app's FK-based design already avoids, nothing to port. Also holds one global "current cuota" cell (`M2 = 36+5+1 = 42`, labelled "IMPORTE CUOTA (+5€) + PRORRATEO HASTA 31/12/2026 (+1€)") and two debtor flags: any `SALDO < -0.01` → "DEUDOR"; `SALDO <= -108` (3 months × 36€) → an escalation flag feeding the hidden `+ de tres recibos` ("more than three [unpaid] receipts") sheet.
- `Cargos` / `Pagos` / `Devoluciones` — three append-only entry logs (one per transaction type: `B CARGOS`/`C PAGOS`/`D DEVOLUCIONES`), each row: Fecha, Acción, Apellidos+Nombre, Número de Socio, Forma de pago, Observaciones, a processed-flag, Mes de Cargo (período), Importe. Maps almost 1:1 onto `Transaccion` — **except** `Devolución` here means a **bounced/returned bank direct debit** (a failed `pago` that needs re-charging), not money paid back to a member. The app's `tipo="reembolso"` currently means the opposite. **This is a real semantic mismatch to resolve with the user before wiring balance logic to `Transaccion.tipo` — not something to guess past.**
- Each bounced-debit row in `Devoluciones` is paired with a `RECARGO` row; across 80 paired rows the recargo/devolución ratio is **exactly 0.10 in 57 of them** (the rest cluster around 0.086–0.101, likely bank-fee rounding/manual-entry noise) — the real-world source of `ReglaCobro.penalizacion`: a 10% surcharge on a bounced direct debit, currently a manually-entered second ledger line rather than a computed value.
- Monthly template sheets (`Cargos Todos Socios STD`, `Agosto 2026+NO`, `Septiembre 2026`, one per período back to `Enero 2025`) — pre-populated with the full active roster; each row's `Importe` formula points at the single `ALTA (SALDO)!$M$2` cell above, so every member is charged the same amount for a given período by default. This is the manual "generate this month's charges" step a human runs — closest legacy analogue to an automated "batch-create cargos for the open período" action, which the app has no equivalent of (candidate addition to 2.6, not built).
- `SALDOS POR SOCIO` (Excel table `Tabla6`) — the actual ledger: one row per transaction once copied over by a macro (see below), with Cargos/Pagos/Devoluciones derived by `IF(Acción=...)` and a **cumulative running `SALDO`** (`Pagos − Cargos − Devoluciones`, running total) computed over **all time**, never scoped or reset per período. This is `SaldoSocios`' real-world origin, but it does **not** match the model's per-`(numero_socio, id_periodo)` row shape. **Open question this analysis surfaces but doesn't resolve: should `SaldoSocios.saldo_actual` be período-scoped (per the current schema) or a continuous running total (per legacy)? Needs a user decision before 2.5 is implemented.**
- `Saldo Anterior` ("SALDO 2024") — a one-time, manually-produced year-opening snapshot carrying each member's prior-year balance forward. Confirms `SaldoSocios.saldo_anterior` is an **annual** carry-over checkpoint (a discrete "close year" action), not something derived automatically period-to-period.
- `CONFIGURACIÓN` — pure dropdown/validation source lists, **no numeric rates anywhere in it**: Mes de Cargo labels, Formas de pago (`REMESA`, `REMESA/CARENCIA`, `EFECTIVO`, `TRANSFERENCIA`, `TRANSFERENCIA/EFECTIVO`, `BAJA`), a Devolución/Recargo list, and the three Acción tags. `BAJA` doubles as a forma-de-pago value meaning "member has left," conflating payment method with membership status — the app's separate `Socio.estado` is already cleaner; nothing to port.
- `Busqueda por socio` — a tiny ad hoc single-member lookup (paste a name, `VLOOKUP` pulls their saldo). Confirms the still-open per-socio balance detail view need already noted in `CLAUDE.md`'s table→screen mapping (`saldos_socios` → "derived per-socio balance display," no screen built yet).
- **No literal "descuento" text anywhere in the workbook, and no formula-driven rate cells at all beyond the 10% recargo pattern above.** `ReglaCobro.descuento` has **no legacy precedent** — flag to the user rather than inventing a formula. `ReglaCobro.plazo_pago` has only weak evidence: comments reference "recargo applies after day 10," i.e. roughly a 10-day payment window — confirm with the user before hardcoding.

**VBA macros** (decompiled via `oletools.olevba` from `xl/vbaProject.bin`): only 3 non-empty procedures, all Excel-UI workarounds, **no hidden business-rule logic**:
- `Worksheet_Change` (×2, near-duplicate) on `SALDOS POR SOCIO` — typing a número in a filter box auto-filters the ledger table to that member and recomputes a running balance over the visible rows.
- `PasarFilasATabla6_Rapido` / `ProcesarTabla` — appends not-yet-processed rows from `Cargos`/`Pagos`/`Devoluciones` into `SALDOS POR SOCIO`'s ledger table, marking them processed. The manual "commit this batch to the ledger" step — the app's direct-to-DB `add_transaction` already makes this obsolete.
- `CalcularSaldoVisibleSimple` — recomputes a running balance only over currently-visible rows (an Excel filter limitation workaround).

**Mapping (workbook concept → planned/existing app feature)**:

| Legacy concept | App feature | Status |
|---|---|---|
| `Cargos`/`Pagos`/`Devoluciones`(bounced)+`RECARGO` logs | `Transaccion` (2.4) | Done, but see the reembolso/devolución semantic mismatch above |
| Global current-cuota cell (`36+5+1`) | `ReglaCobro.cuota_mensual` (2.5/2.7) | Legacy has one club-wide value, not multiple named rules — recommend treating it as one active rule for now |
| Devolución + 10% recargo | `ReglaCobro.penalizacion` (2.5/2.7) | Recommend auto-computing 10% of the bounced amount rather than a manual second entry |
| "día 10" recargo-trigger comment | `ReglaCobro.plazo_pago` (2.7) | Weak evidence (~10 days) — confirm with the user |
| *(nothing found)* | `ReglaCobro.descuento` (2.7) | No legacy precedent at all |
| Monthly template sheets + `PasarFilasATabla6_Rapido` | Batch charge-generation per período (2.6) | Not built — candidate new sub-feature |
| `SALDOS POR SOCIO` running balance | `SaldoSocios.saldo_actual` (2.5) | Continuous total vs. this app's período-scoped rows — **needs a decision, see above** |
| `Saldo Anterior` year snapshot | `SaldoSocios.saldo_anterior` (2.5) | Confirmed: annual carry-over, not period-to-period |
| `-108` / `+ de tres recibos` debtor escalation | none yet | Candidate for 2.8/2.9 (reports/alerts), not scoped |
| `Busqueda por socio` | per-socio balance detail view | Still the open `saldos_socios` screen gap noted in `CLAUDE.md` |
| VBA macros | none | Pure Excel workarounds; DB-backed queries already supersede them |

**Decided (workflow, unchanged):** analyze and document first, agree on the implementation mapping with the user, *then* implement inside the relevant `features/<domain>/` package — not a direct/blind port of VBA into Python. This entry is that analysis-and-mapping deliverable; 2.5/2.7's actual implementation is still gated on the user resolving the open questions above (devolución-vs-reembolso semantics, período-scoped vs. continuous balance, `plazo_pago`/`descuento` values).
- Depended on: the user attaching the `.xlsm` file — **done**, analyzed 2026-08-08.

### 2.15c Second legacy workbook — club-wide accounting (not yet scoped)
- **New request**, surfaced while doing 2.15b's analysis. Alongside the per-member dues workbook analyzed above, the club runs a **second, separate** legacy file — `A Nuevo Excel Diario Club Paraiso (version 5.10) 2026 Macro.xlsm` — covering **club-wide day-to-day accounting**: purchases, salaries, and general bookkeeping beyond individual member dues.
- **Deliberately deferred per the user** — not the same domain as 2.15b's workbook, to be analyzed separately later. Not started: no sheet/macro inspection done, no mapping to any planned app feature.
- README/`CLAUDE.md` currently only describe member-dues-shaped functionality (transactions/balances/periods scoped to `Socio`/`numero_socio`). This second workbook implies a **club-wide finances domain the plan doesn't cover at all yet** (e.g. an expense/`Gasto` concept, salaries, non-member-attributed income/outflow) — keep this in mind as a distinct future chunk once picked up, not folded into 2.4/2.5's member-balance work.

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
2. **Periods, Reports screens** — don't exist yet, not even as a skeleton (`features/periods/`, `features/reports/` haven't been created). `features/members/`, `features/settings/`, and now `features/transactions/` (2.4, done) follow the per-domain folder pattern documented in `CLAUDE.md`.
3. **Overall visual/UI polish.** Bug 1.2 covers one specific rendering defect (the broken QSS header-color rule), but there's no wider design work planned yet: today the app is three hand-written QSS strings (`MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET`, `SETTINGS_MENU_STYLESHEET` in `styles.py` — the latter two already near-duplicates of each other) plus Qt's built-in `QStyle.SP_*` stock icons (no custom icon set, no consistent spacing/typography system, no light/dark theme, no design tokens). **Decided**: no specific reference given — Claude proposed a clean, modern look (palette, spacing, icons) for approval before wider rollout; see [`UI_PROPOSAL.md`](UI_PROPOSAL.md) for the full audit and design direction (token layer, unified ledger palette, `qtawesome` icons, extracted shared table/toolbar composition for future screens).
4. **Table row selection doesn't survive navigating away and back.** Reported by the user: selecting a row in a grid (Members, Transacciones, Métodos de pago, Reglas de cobro), then clicking outside the table or navigating away (e.g. "Volver" back to the main menu) and returning to the same screen, loses the selection — the row shows unselected again instead of staying selected. Root cause is almost certainly that every screen's `load_table_view()`/`refresh_table()` rebuilds the `QStandardItemModel` from scratch (`removeRows` + `appendRow` for every row), which discards the `QItemSelectionModel`'s selection since it's keyed to model indices that no longer exist after rebuild — same class of problem `TableSortMixin` already solves for sort state, just not yet done for selection. Fix should remember the selected row's stable id (e.g. `id_socio`/`id_transaccion`/`id_metodo`/`id_regla`, whichever column 0 holds) before a reload and re-select the matching row after repopulating, across all four grid screens.

---

## 5. Recommended order of work

1. **Quick bugs** (section 1) — low effort, avoids future confusion.
2. **Minimal testing infrastructure** — `pytest` + first tests over what already exists and persists (`MembersService.add_member`, `ViewRegistry`, sort functions). This provides a safety net before touching more business logic.
3. **Complete the Members CRUD** — real search (2.3), editing (2.1), logical deactivation with confirmation (2.2, 4.3), audit logging (2.12) on every write operation, and retiring the generic "Vistas" table-switcher in favor of a proper members-only load path (2.16). This fully closes out the one partially-built domain before opening a new one.
4. **Seed data + Settings** — fixed payment methods and billing rules (2.7), since the transactions module depends on payment methods existing. Add the **database reset action** (2.15) to the same Settings screen while it's being built.
5. **Transactions module** (2.4) — done, except balance recalculation (see next item).
6. **Balance calculation and Periods** (2.5, 2.6) — depends on transactions existing (done); 2.15b's `.xlsm` analysis is now done (see 2.5/2.15b), but implementation is still gated on the user resolving the open questions it surfaced (período-scoped vs. continuous balance, devolución-vs-reembolso semantics) before writing code. A full Periods management screen is still unbuilt.
7. **Business-standard test scenarios** (3.8) — once the rules they encode (2.4, 2.5, 2.6, 2.7) actually exist, write the acceptance-style scenarios that pin down correct behavior for late payments, penalties, discounts, rejected refunds, and balance carry-over.
8. **Reports + export** (2.8), then **charts/statistics** (2.9).
9. **Backups** (2.10) and **import** (2.11) — more independent features, can be tackled in parallel or at the end.
10. **Long-term non-functionals**: Alembic (a technical prerequisite — move it earlier if the schema starts changing a lot), encryption (2.13), Postgres migration (2.14) — these come into play once the functional domain is more mature and there's real data to protect.
11. **Visual/UI polish** (4.3) — best done once the screens it applies to actually exist (transactions/periods/reports), so styling isn't reworked twice; earlier if the user wants the look-and-feel decided up front instead.
12. **Titular per numero_socio** (2.17) — done, see §2's Completed block for `feat/titular-por-numero-socio`.

---

## 6. Decisions (resolved)

All previously open questions have been answered by the user; nothing outstanding here for now.

- **Delete-member semantics**: soft delete only — "Eliminar" always sets `estado = "inactivo"`, never a physical `DELETE`. See 2.2.
- **Export format priority**: Excel first (`openpyxl`), PDF later. See 2.8.
- **Postgres migration / encryption timeline**: long-term goals, not scheduled now — keep `create_all`/SQLite until the functional domain is mature. See 2.13, 2.14.
- **UI redesign direction**: no specific reference from the user — Claude proposed a design (palette, spacing, icons) in [`UI_PROPOSAL.md`](UI_PROPOSAL.md), pending approval before wide rollout. See 4.3.
- **Transactions navigation model**: both entry points, not either/or — the Members toolbar's "Registrar" button stays as a socio-pre-filled shortcut, *and* a standalone `Transacciones` screen is added to the main menu for club-wide browsing/filtering (README's fecha/tipo/estado filter requirement needs the standalone screen; the quick shortcut alone couldn't satisfy it). Both share one dialog and one service. See 2.4.
- **Transaction integrity rules**: a reembolso can't exceed (sum of pago − sum of already-refunded reembolso) scoped to the same numero_socio+período; an exact-duplicate Transaccion (same numero_socio/tipo/monto/id_periodo/id_metodo/fecha) is rejected. See `CLAUDE.md`'s `features/transactions/service.py` section.
- **Balance recalculation sequencing**: deferred until the legacy `.xlsm` (2.15b) is analyzed, rather than guessing at the formula while building the transactions module. See 2.5.
- **Titular model**: `Socio.es_titular` boolean, auto-unset-other-on-set (with a UI swap confirmation), a brand-new `numero_socio` must get a titular immediately, existing `numero_socio` groups are left unset/blocked from registering transactions — via *both* the open picker and the Members-toolbar "Registrar" shortcut, not just the search picker — until an admin assigns one manually (no auto-backfill). See `CLAUDE.md`'s `features/members/toolbar_service.py` and `features/transactions/` sections.
- **Automatic período rollover**: triggered by app-start/navigation (not on-transaction, not a scheduled job) — if today's date isn't covered by any existing período, auto-create the next one using the same monthly-length derivation as `create_periodo_rapido`, and auto-close the previously-open período so only one is ever `abierto` at a time. See 2.6.
