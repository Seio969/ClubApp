# ClubApp — Current state and pending work plan

_Generated: 2026-08-08. Based on direct inspection of the code in `src/`, `README.md`, `db.md`, `pyproject.toml`, and `CLAUDE.md`._

## 0. Executive summary

The project is at an **early-mid stage**: the "Gestionar Miembros" (Manage Members) screen, a "🧾 Transacciones" screen, and a "⚙️ Ajustes" (Settings) hub are wired up. Within Members, member CRUD (search/create/edit/deactivate) is fully implemented, persisted, and audit-logged — export remains a logging placeholder. Transaction registration is real (shared `TransactionDialog`, both a Members "Registrar" shortcut and the standalone Transacciones screen), with integrity validation and automatic balance calculation (`SaldoSocios`, 2.5), but period management beyond a minimal quick-create is still unbuilt. Within Ajustes, payment methods and billing rules both have full CRUD (soft-deactivation only, same pattern as members), a read-only audit log viewer exists, and a database reset action (full wipe + scoped reset, type-to-confirm safety flow) exists. The rest of the financial functionality described in `README.md` (balances, periods, reports, backups, import) **has no UI or service implemented at all**, even though the ORM schema for almost everything already exists in `models.py`. There is a `pytest` suite (see §3) but no linter, no type-checker, and no CI configured.

This document lists, by category, everything that's pending and proposes an execution order.

---

## 1. Known bugs

### 1.1 Transaction dialog socio picker showed few/no choices — NOT A BUG, was missing data
- **Reported 2026-08-12, investigated same day, closed - no code bug found.** Initially suspected two issues: a `currentData()`/typed-text sync defect in `TransactionDialog`'s socio combo, and the picker showing "only 3" then "none" of the socios. Root cause of the visible symptom: the current DB's data had 401 distinct `numero_socio` groups but **zero with an active titular** (data looked bulk-inserted rather than entered through `MembersService.add_member`, which is what normally forces a titular on a new `numero_socio`), and the picker's deliberate "only show groups with an active titular" rule (PLAN.md 2.17) correctly showed nothing as a result. **Resolved by the user assigning titulares directly** - confirmed working correctly afterward, with no code change needed. A `currentData()`/typed-text mismatch fix was drafted and then reverted per the user - not a real-world issue in practice.

### 1.2 Members grid: cells become editable after sorting by column header — FIXED
- **Found and fixed 2026-08-12** (reported by user, thought this was already fixed previously). `features/members/table_sort.py`'s `_apply_sort()` rebuilds the table's `QStandardItemModel` with fresh `QStandardItem`s on every header-click sort, but - unlike the initial load path (`menu_service.py`'s `_populate_model`) - never called `item.setEditable(False)` on them. So the Members grid's non-editable-cells rule held on first load but silently broke the moment a user sorted by clicking a column header, letting double-click open an editor. Fixed by adding the same `setEditable(False)` loop to `_apply_sort`'s rebuild; regression test added (`tests/test_table_sort.py::TestApplySortKeepsCellsNonEditable`, confirmed it fails against the old code). Settings screens (`metodos_pago`/`reglas_cobro`) don't use `TableSortMixin` and were unaffected.

## 2. Critical business functionality — not implemented

Members CRUD, seed data + Settings (payment methods/billing rules CRUD, DB reset), the transactions module including balance recalculation (2.5), titular-per-`numero_socio`, estado-aware member filtering, and the audit log viewer are all done — see git history / `CLAUDE.md` for detail.

Everything below already has an ORM model declared in `models.py` but **zero UI and zero service logic**, except where noted above:

**Completed:**
- [x] Balance calculation and carry-over (`SaldoSocios.saldo_actual`, 2.5) — `BalancesService`, triggered automatically from `TransactionsService.add_transaction`; see `CLAUDE.md`'s balance formula entry (PR TBD).

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
- `Cargos` / `Pagos` / `Devoluciones` — three append-only entry logs (one per transaction type: `B CARGOS`/`C PAGOS`/`D DEVOLUCIONES`), each row: Fecha, Acción, Apellidos+Nombre, Número de Socio, Forma de pago, Observaciones, a processed-flag, Mes de Cargo (período), Importe. Maps almost 1:1 onto `Transaccion` — **except** `Devolución` here means a **bounced/returned bank direct debit** (the bank rejects a `pago`, which then needs re-charging), not money paid back to a member. **Confirmed by the user (2026-08-08): devolución and reembolso are genuinely different concepts, not a naming overlap to paper over.** The app's `Transaccion.tipo` enum (`cargo`/`pago`/`reembolso`) has **no equivalent today for "the bank rejected this pago"** — that's a real gap, not just a documentation nuance: modeling it needs either a fourth tipo (e.g. `devolucion`) or some other way to mark a `pago` as bounced, plus the paired 10% recargo (see below). Design that concretely before touching 2.4/2.5's code, don't bolt it onto `reembolso`.
- Each bounced-debit row in `Devoluciones` is paired with a `RECARGO` row; across 80 paired rows the recargo/devolución ratio is **exactly 0.10 in 57 of them** (the rest cluster around 0.086–0.101, likely bank-fee rounding/manual-entry noise) — the real-world source of `ReglaCobro.penalizacion`: a 10% surcharge on a bounced direct debit, currently a manually-entered second ledger line rather than a computed value.
- Monthly template sheets (`Cargos Todos Socios STD`, `Agosto 2026+NO`, `Septiembre 2026`, one per período back to `Enero 2025`) — pre-populated with the full active roster; each row's `Importe` formula points at the single `ALTA (SALDO)!$M$2` cell above, so every member is charged the same amount for a given período by default. This is the manual "generate this month's charges" step a human runs — closest legacy analogue to an automated "batch-create cargos for the open período" action, which the app has no equivalent of (candidate addition to 2.6, not built).
- `SALDOS POR SOCIO` (Excel table `Tabla6`) — the actual ledger: one row per transaction once copied over by a macro (see below), with Cargos/Pagos/Devoluciones derived by `IF(Acción=...)` and a **cumulative running `SALDO`** (`Pagos − Cargos − Devoluciones`, running total) computed over **all time**, never scoped or reset per período. This is `SaldoSocios`' real-world origin. **Decided (2026-08-12): `saldo_actual` is a continuous running total, achieved by chaining `saldo_anterior` forward at every período transition — see `CLAUDE.md`.**
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
| `Cargos`/`Pagos`/`Devoluciones`(bounced)+`RECARGO` logs | `Transaccion` (2.4) | cargo/pago/reembolso/devolución all done, including balance-validation (2.5: Reembolso and Devolución share the "available pagos" pool) — still no auto-computed 10% recargo pairing or a "mark this specific pago as bounced" relationship, just a same-scope amount check. |
| Global current-cuota cell (`36+5+1`) | `ReglaCobro.cuota_mensual` (2.5/2.7) | Legacy has one club-wide value, not multiple named rules — recommend treating it as one active rule for now |
| Devolución + 10% recargo | `ReglaCobro.penalizacion` (2.5/2.7) | Recommend auto-computing 10% of the bounced amount rather than a manual second entry |
| "día 10" recargo-trigger comment | `ReglaCobro.plazo_pago` (2.7) | **Decided (2026-08-12): 10 days** |
| *(nothing found)* | `ReglaCobro.descuento` (2.7) | **Decided (2026-08-12): no legacy precedent — leave unused/manual-only, no discount logic built** |
| Monthly template sheets + `PasarFilasATabla6_Rapido` | Batch charge-generation per período (2.6) | Not built — candidate new sub-feature |
| `SALDOS POR SOCIO` running balance | `SaldoSocios.saldo_actual` (2.5) | **Decided (2026-08-12): continuous running total**, chained via `saldo_anterior` every período — see `CLAUDE.md` |
| `Saldo Anterior` year snapshot | `SaldoSocios.saldo_anterior` (2.5) | Confirmed: annual carry-over, not period-to-period |
| `-108` / `+ de tres recibos` debtor escalation | none yet | Candidate for 2.8/2.9 (reports/alerts), not scoped |
| `Busqueda por socio` | per-socio balance detail view | Still the open `saldos_socios` screen gap noted in `CLAUDE.md` |
| VBA macros | none | Pure Excel workarounds; DB-backed queries already supersede them |

**Decided (workflow, unchanged):** analyze and document first, agree on the implementation mapping with the user, *then* implement inside the relevant `features/<domain>/` package — not a direct/blind port of VBA into Python. This entry is that analysis-and-mapping deliverable.
- **Decided (2026-08-08): devolución (bank-rejected pago) and reembolso (money back to a member) are distinct concepts** — `Transaccion` needs a way to represent the former that it doesn't have today (see the mapping table row above). **`"Devolución"` now exists as a selectable `TIPOS_TRANSACCION` value (2026-08-09)** — closes the "no equivalent tipo at all" gap, but the deeper modeling (bounced-pago linkage, auto recargo) is still not designed.
- **Resolved (2026-08-12):** `saldo_actual` is a continuous running total (not período-scoped), `plazo_pago` = 10 days, `descuento` has no legacy precedent and stays unbuilt — see `CLAUDE.md` for the full decided formula. 2.5 is now built; 2.6 (period management beyond quick-create) is not.
- **Resolved (2026-08-12):** `"Devolución"` now has the balance-validation rule flagged below as "still open" — it shares Reembolso's "available pagos" pool (can't exceed sum of pago minus already-reversed reembolso/devolución for the same numero_socio+período), on the confirmed assumption that a bank-collected charge is always recorded as a `Cargo`+`Pago` pair, with `Devolución` only added later if that `Pago` bounces. See `CLAUDE.md`.
- **Still open, not yet scoped:** a bank-initiated `cargo` (`REMESA`/`TRANSFERENCIA` — see `metodos_pago`) may need to exist as its own concept, separate from a manually-entered `cargo`.
- Depended on: the user attaching the `.xlsm` file — **done**, analyzed 2026-08-08.

### 2.15c Second legacy workbook — club-wide accounting (not yet scoped)
- **New request**, surfaced while doing 2.15b's analysis. Alongside the per-member dues workbook analyzed above, the club runs a **second, separate** legacy file — `A Nuevo Excel Diario Club Paraiso (version 5.10) 2026 Macro.xlsm` — covering **club-wide day-to-day accounting**: purchases, salaries, and general bookkeeping beyond individual member dues.
- **Deliberately deferred per the user** — not the same domain as 2.15b's workbook, to be analyzed separately later. Not started: no sheet/macro inspection done, no mapping to any planned app feature.
- README/`CLAUDE.md` currently only describe member-dues-shaped functionality (transactions/balances/periods scoped to `Socio`/`numero_socio`). This second workbook implies a **club-wide finances domain the plan doesn't cover at all yet** (e.g. an expense/`Gasto` concept, salaries, non-member-attributed income/outflow) — keep this in mind as a distinct future chunk once picked up, not folded into 2.4/2.5's member-balance work.

### 2.18 Calendar (events and reminders)
- **New request** (2026-08-09). A "📅 Calendario" button on the main menu, alongside Miembros/Transacciones/Ajustes, opening a new `features/calendar/` screen (following the same per-domain folder pattern as `features/members/`/`features/transactions/`/`features/settings/`).
- Scope: create/view/edit events and reminders on the calendar. No ORM model exists yet for this — a new table (e.g. `Evento`/`Recordatorio`) needs to be designed in `models.py`, there is no precedent for it in the current schema.
- **Future, explicitly out of scope for now**: email reminders sent to socios who have an `email` on file (`Socio.email` already exists), notifying them about relevant events/reminders. No email-sending mechanism or dependency (e.g. `smtplib`, a transactional-email provider) exists in `pyproject.toml` yet — this is a later addition on top of the calendar itself, not part of its first build.
- **Decided (durable):** the user explicitly wants this left for **very last** in the build order — see §5, item 11. Independent of every other pending item; not blocked by, and doesn't block, anything else in this plan.

---

## 3. Technical debt / infrastructure

1. **No test suite (high priority).**

   **Completed** (branch `chore/testing-infrastructure`): `pytest` added as a dev dependency with `tests/` wired up (`tests/conftest.py`'s `test_engine` fixture isolates every DB-touching test on a throwaway SQLite file), plus first tests for `MembersService.add_member`, `ViewRegistry`, and `TableSortMixin._normalize_for_sort`/`_make_sort_key` (`features/members/table_sort.py`). See `CLAUDE.md`'s `tests/` section for what's covered and the fixture's engine-patching gotcha.

   **Still pending:**
   - `pytest-qt` — deferred, no test yet needs a real `QApplication`.
   - Aggressively separating pure logic (services: `toolbar_service.py`, `menu_service.py`, `transactions/service.py`, `balances/service.py`) from the Qt layer beyond what's already service-separated.
   - No Qt-level tests yet (views/dialogs/toolbars) — `get_member`/`update_member`/`set_socio_estado`/`search_members` now have service-level coverage (see `CLAUDE.md`'s `tests/` section), but nothing exercises the toolbar's confirmation dialog or dialog pre-fill through a real `QApplication`. No coverage of exports.
2. **No linter/formatter/type-checker.** No `ruff`, `black`, or `mypy` in `pyproject.toml`. Since the code already uses type hints (`Optional`, `dict[str, Any]`, etc.), `mypy` or `pyright` would add real value, especially in the service layer.
3. **No CI.** No `.github/workflows/`. Once a test suite exists, adding a minimal workflow (`uv sync` + `pytest`) would catch regressions like the `on_refresh` indentation bug — though a linter would have caught that one too (even if not as a syntax error).
4. **`db.sql` and `db.md` are out of date** relative to `models.py` (a `forma_pago`/`estado` columns in `db.sql` that don't exist on the ORM; `id_usuario`/`usuarios` naming in `db.md` that doesn't match `id_socio`/`socios`). Decide: keep them manually in sync every time `models.py` changes, or generate them automatically (e.g. with `sqlalchemy-schemadisplay` or similar) so they can't drift again.
6. **No migrations (Alembic).** Any column change today requires manually deleting the `.db`; as the schema grows (transactions, balances, etc.) this becomes risky for a club's real data. Introduce Alembic soon, before there's production data to protect.
8. **Business-standard test scenarios.** **New request** — not previously in this plan. Distinct from unit tests over individual functions (item 1 above): this is a set of named, documented scenarios that encode the club's actual business rules end-to-end, e.g. "member pays full quota on time", "member pays late → penalty from `ReglaCobro` applied", "discount rule applied correctly", "refund attempted with no prior payment → rejected" (2.4's integrity rule), "period closed → new transactions against it are rejected" (2.6), "balance carried over correctly from a closed period to the next open one" (2.5). These should live as acceptance-style tests (e.g. `tests/scenarios/`) once pytest is in place (item 1), each scenario asserting the final DB state against the business rule it documents. The user has a separate realistic fake-data generator (one level above this repo) they intend to wire into the workspace later for populating the DB with sample data for manual testing/demos — that's a different, complementary concern from these business-rule scenarios, which are about *correctness*, not data volume.

---

## 4. Pending UI / UX

1. **Periods, Reports screens** — don't exist yet, not even as a skeleton (`features/periods/`, `features/reports/` haven't been created). `features/members/`, `features/settings/`, and now `features/transactions/` (2.4, done) follow the per-domain folder pattern documented in `CLAUDE.md`. `features/calendar/` (2.18) is the same story, but deliberately last — see below.
2. **Overall visual/UI polish.** There's no wider design work planned yet: today the app is three hand-written QSS strings (`MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET`, `SETTINGS_MENU_STYLESHEET` in `styles.py` — the latter two already near-duplicates of each other) plus Qt's built-in `QStyle.SP_*` stock icons (no custom icon set, no consistent spacing/typography system, no light/dark theme, no design tokens). **Decided**: no specific reference given — Claude proposed a clean, modern look (palette, spacing, icons) for approval before wider rollout; see [`UI_PROPOSAL.md`](UI_PROPOSAL.md) for the full audit and design direction (token layer, unified ledger palette, `qtawesome` icons, extracted shared table/toolbar composition for future screens).

---

## 5. Recommended order of work

The original ordering (quick bugs, minimal testing infrastructure, Members CRUD completion, seed data + Settings incl. database reset, the transactions module minus balance recalculation, titular per `numero_socio`, the numeric validator scientific-notation fix, non-editable grid cells + a Refrescar/search-filter bug fix) is done — see git history for detail.

**Next:**
1. **Period management** (2.6) — 2.5 (balance calculation) is done; a full Periods management screen (open/close, rollover) is still unbuilt.
2. **Business-standard test scenarios** (3.8) — once the rules they encode (2.4/2.5/2.7 done, 2.6 pending) actually exist end-to-end.

**Then — larger, independent features:**
3. **Reports + export** (2.8), then **charts/statistics** (2.9).
4. **Backups** (2.10) and **import** (2.11) — can be tackled in parallel or at the end.
5. **Long-term non-functionals**: Alembic (a technical prerequisite — move it earlier if the schema starts changing a lot), encryption (2.13), Postgres migration (2.14).
6. **Visual/UI polish broader pass** (4.3) — the token layer/`qtawesome` icons/shared "data screen" composition extraction from `UI_PROPOSAL.md`, distinct from the targeted fixes above; best done once transactions/periods/reports screens exist so styling isn't reworked twice.
7. **Second legacy workbook analysis** (2.15c) — deliberately deferred by the user; pick up whenever prioritized, independent of everything else in this list.
8. **Calendar** (2.18) — main-menu "📅 Calendario" screen for events/reminders, with email reminders to socios as a later follow-up. **Deliberately the very last item in this entire plan**, per explicit user instruction (2026-08-09) — not to be pulled forward ahead of anything else above, even if it looks small/independent enough to slot in earlier.

---

## 6. Decisions (resolved)

Most previously open questions have been answered by the user. **Exception:** the bank-initiated-`cargo` concept (flagged 2026-08-09) remains deliberately deferred — see 2.15b.

- **Balance formula and scope** (2026-08-12): `SaldoSocios.saldo_actual` is a continuous running total (not período-scoped) via `saldo_anterior` chaining every período; formula is `saldo_anterior + cargos − pagos + reembolsos + devoluciones` (reembolso and devolución both add back to what's owed - a reembolso hands cash back to the socio, undoing part of a prior pago, the same direction as a devolución reversing a bounced one); `ReglaCobro.plazo_pago` = 10 days; `ReglaCobro.descuento` has no legacy precedent and stays unbuilt; overpayment a socio wants left as credit (rather than refunded via Reembolso) needs no separate discount logic - it carries forward automatically via the `saldo_anterior` chain. `SaldoSocios` gained `reembolsos`/`devoluciones` columns (alongside the existing `cargos`/`pagos`) so each tipo's contribution stays separately queryable. Full detail in `CLAUDE.md`'s "Key invariants & durable decisions". See 2.5, 2.15b.
- **Devolución balance-validation rule** (2026-08-12): Devolución shares Reembolso's "available pagos" pool - their combined total can't exceed sum of pago for the same numero_socio+período - built on the confirmed assumption that a bank-collected charge is always recorded as a Cargo+Pago pair, with Devolución only added later if that Pago bounces. See 2.4/2.5's `_validate_transaction`.

- **Delete-member semantics**: soft delete only — "Eliminar" always sets `estado = "inactivo"`, never a physical `DELETE`. See 2.2.
- **Export format priority**: Excel first (`openpyxl`), PDF later. See 2.8.
- **Postgres migration / encryption timeline**: long-term goals, not scheduled now — keep `create_all`/SQLite until the functional domain is mature. See 2.13, 2.14.
- **UI redesign direction**: no specific reference from the user — Claude proposed a design (palette, spacing, icons) in [`UI_PROPOSAL.md`](UI_PROPOSAL.md), pending approval before wide rollout. See 4.3.
- **Transactions navigation model**: both entry points, not either/or — the Members toolbar's "Registrar" button stays as a socio-pre-filled shortcut, *and* a standalone `Transacciones` screen is added to the main menu for club-wide browsing/filtering (README's fecha/tipo/estado filter requirement needs the standalone screen; the quick shortcut alone couldn't satisfy it). Both share one dialog and one service. See 2.4.
- **Transaction integrity rules**: reembolso and devolución together can't exceed sum of pago (each reduces the same "available pagos" pool) scoped to the same numero_socio+período; an exact-duplicate Transaccion (same numero_socio/tipo/monto/id_periodo/id_metodo/fecha) is rejected. See `CLAUDE.md`'s `features/transactions/service.py` section.
- **Balance recalculation sequencing**: deferred until the legacy `.xlsm` (2.15b) is analyzed, rather than guessing at the formula while building the transactions module. See 2.5.
- **Titular model**: `Socio.es_titular` boolean, auto-unset-other-on-set (with a UI swap confirmation), a brand-new `numero_socio` must get a titular immediately, existing `numero_socio` groups are left unset/blocked from registering transactions — via *both* the open picker and the Members-toolbar "Registrar" shortcut, not just the search picker — until an admin assigns one manually (no auto-backfill). See `CLAUDE.md`'s `features/members/toolbar_service.py` and `features/transactions/` sections.
- **Automatic período rollover**: triggered by app-start/navigation (not on-transaction, not a scheduled job) — if today's date isn't covered by any existing período, auto-create the next one using the same monthly-length derivation as `create_periodo_rapido`, and auto-close the previously-open período so only one is ever `abierto` at a time. See 2.6.
