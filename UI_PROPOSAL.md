# ClubApp UI — Audit & Redesign Direction

_Design proposal — internal review draft. No implementation in this pass; file:line references point at the state of the repo at the time of this audit._

**Audience:** club administrator / president (single power user)
**Scope:** full app — screens built today plus the ones `README.md` and the menu bar's stubs imply are still coming
**Framework:** kept as-is — PySide6 / Qt
**Locked:** Spanish domain naming stays (Socio, Transacción, Periodo, …)

---

## 1. Audit — what's actually there today

Only the Members screen is fully wired; everything else is a menu-bar stub or a README requirement with no UI yet.

### UI stack

| Layer | Current implementation |
|---|---|
| Framework | PySide6 (Qt widgets) — no QML, no web view. |
| Component library | None. Raw `QWidget`/`QToolBar`/`QTableView`. Icons are Qt's built-in `QStyle.SP_*` stock glyphs (file, trash, reload) — generic desktop-chrome icons, not a chosen set. |
| Styling | Qt Style Sheets (QSS) as Python strings in `src/ui/styles.py` — two large per-screen blocks (`MAIN_MENU_STYLESHEET`, `MEMBERS_MENU_STYLESHEET`) plus two loose inline snippets (`TITLE_STYLE`, `BUTTON_FONT_STYLE`) applied directly to individual widgets, outside the cascade. |
| State / data | No app-level state layer. `QStandardItemModel` holds table data directly; query/CRUD logic lives in per-feature `*_service.py` classes called straight from view/toolbar handlers. Navigation is one `QStackedWidget`; screens reach into `main_window._stack`/`._home` directly rather than through a shared router. |

### Architecture map

The `features/<domain>/` convention (view + toolbar + dialog + services co-located) is sound, and only `members/` exists yet:

```
src/
  ui/                     shell — styles.py, main_window.py, views/
  common/                 view_registry.py — generic table browsing
  database/               models.py, session.py
  features/
    members/              ✓ built — view, toolbar, dialog, services
    transactions/          planned — cargos/pagos/reembolsos (README)
    periods/               planned — abrir/cerrar periodos
    reports/               planned — resúmenes, gráficas, export
    settings/               planned — reglas de cobro, config
```

### Pain points found

Reading `members/` as the template every future feature will likely copy:

1. **No shared token layer.** Every color is a raw hex literal, duplicated across two unrelated QSS blocks. A future `transactions/` screen has nothing to import from — it would either invent its own colors or hand-copy strings.
   `ui/styles.py:13–90`

2. **The two existing screens don't read as one product.** Main menu: solid black background, green gradient buttons. Members screen: flat `#fafafa`, plain grey outlined back-button. No shared visual identity connects them.
   `ui/styles.py:13–51` vs `54–90`

3. **A QSS rule is dead on arrival.** A header-text-color fix was attempted using `#`-prefixed lines as comments — QSS doesn't support that syntax, so the rule never applies and a stray `}` is left dangling. Qt swallows it silently; header text color is whatever the platform theme gives it.
   `ui/styles.py:86–89`

4. **A refresh action can go silently inert.** `on_refresh`'s fallback log line is mis-indented to class-body level, so it runs once at import time instead of on every click with no working parent — clicking "Refrescar" with no reachable `refresh_table` does nothing, with no log trace to explain why.
   `features/members/toolbar.py:137–154`

5. **Home-menu routing is a string match on an emoji.** Buttons dispatch via `button.startswith("🧑‍🤝‍🧑")` rather than an id — brittle already, and won't scale cleanly to the four-plus buttons transactions/periods/reports/settings will add.
   `ui/views/main_menu_widget.py:77–81`

6. **No keyboard-focus state exists anywhere** in either QSS block, and no dark-mode or high-contrast alternative — worth flagging since this is a daily data-entry tool, not a browse-once screen.
   `ui/styles.py`

7. **Sizing is pixel-fixed, not layout-driven.** `MainWindow.resize(900, 600)` has no paired `setMinimumSize`; home-menu buttons are hardcoded to 400×40px. No high-DPI policy is set in `run_main_window` — Qt6 defaults usually cope, but nothing here was deliberately chosen.
   `ui/main_window.py:36`, `ui/views/main_menu_widget.py:68–69`

---

## 2. Proposal — a direction for the next pass

PySide6 and the `features/<domain>/` folder shape both stay — the gap isn't the framework, it's that nothing yet gives new screens a shared visual or structural foundation to build on.

### Structure

| Change | Why |
|---|---|
| Add a token module (e.g. `ui/theme.py`) that `styles.py`'s QSS strings build from | One palette to change instead of hunting hex literals across every screen's stylesheet. |
| Split each screen's one large QSS blob into small fragments (buttons, table, toolbar) assembled per screen | Lets Members and a future Transactions screen share the table/toolbar fragment instead of re-deriving it. |
| Extract a reusable "data screen" composition from `members/` (search bar + toolbar + sortable table is already ~90% generic) | `column_fill.py` and `table_sort.py` are already domain-agnostic; without extraction, transactions/periods/reports each re-implement or copy-paste them. |
| Give transactions/periods/reports/settings the same view/toolbar/dialog/service shape as `members/` | Matches the convention already stated in the project docs — this formalizes it before three more screens get built ad hoc. |
| Fix the QSS dead-comment and `on_refresh` indentation bugs in the same pass | Both directly undercut "polish" — no point shipping a new palette on top of a header-color rule that silently never fires. |

### Color system

The current app reads as two identities stitched together — a black-and-neon-green landing splash, then a flat grey enterprise table. For a club president's daily working tool, unify both around one calmer, ledger-like palette: legible for long table-reading sessions, with the green identity kept but controlled rather than gradient-washed across every button.

| Swatch | Hex | Role |
|---|---|---|
| Paper | `#F7F7F4` | App & table background |
| Ink | `#1F2A24` | Primary text |
| Pine (accent) | `#2F6B52` | Primary actions, active state |
| Pine soft | `#DCEAE0` | Hover / selected row |
| Hairline | `#D9D6CC` | Borders, table rules |
| Warning | `#B8862B` | Pending / overdue balance |
| Danger | `#A1382F` | Failed payment, delete confirm |

One accent doing real work (primary actions, active view) instead of a gradient covering every button equally, so the eye can still find what's clickable versus informational.

**Rationale:** Ink-on-paper and paper-on-accent are both built to clear WCAG AA (4.5:1) for body text — worth a final contrast check with the exact rendered QSS colors at implementation time, since Qt doesn't enforce this for you. Warning/danger are kept separate from the accent hue deliberately: this is a money app (dues, refunds, overdue balances) and today nothing in the UI distinguishes state at a glance — the whole interface is currently either black, green, or grey regardless of what a row means. Pure `#000000` for the main menu is dropped in favor of the same paper/ink pairing used everywhere else — full black reads as a login/kiosk screen, not a tool someone reopens for two hours of data entry.

### Dependencies — keep / swap / supplement

| Package | Decision | Reason |
|---|---|---|
| PySide6 | Keep | Fits the offline-desktop, single-admin, SQLite use case; no reason to move to a web/Electron stack for one user. |
| SQLAlchemy + SQLite | Keep | Untouched by a UI-layer proposal; README's Postgres-migration path stays open either way. |
| `qtawesome` (or a small bundled SVG set) | Supplement | Replaces the generic `QStyle.SP_*` stock icons with a cohesive set for Nuevo/Editar/Eliminar/Registrar — tiny dependency, works fully offline. |
| `openpyxl` | Supplement | Not a visual change, but the Exportar toolbar button already exists and does nothing — README requires Excel/PDF export and `utils/exporters.py` is currently empty. |
| `qt-material` / full theming frameworks | Skip | Would fight the palette above and add a heavier dependency for a single-window app; a hand-rolled token module is simpler and gives full control over this specific identity. |

### Accessibility & responsive notes

Single-user desktop tool, not a public responsive web app, so the bar is different — but a few things are worth fixing regardless:

- Add a visible `:focus` state (currently absent everywhere) — matters for a keyboard-driven data-entry tool more than for a browse-once page.
- Fix the dead header-color QSS rule as part of the palette pass, and re-verify contrast with the exact rendered values, not the source hex — Qt's cascade/inheritance can shift the final color.
- Replace fixed-pixel button/window sizing with size policies and `setMinimumSize` — extend the layout-driven approach `ensure_columns_fill` already uses for the table to the main menu and dialogs, so the window stays usable when resized down on a laptop.
- Confirm Qt6's default high-DPI handling looks right on the president's actual monitor — nothing currently overrides it, so this is a smoke-test item, not necessarily a code change.

---

## 3. Layout mockups — how this looks screen by screen

ASCII wireframes at the proposed structure — not pixel-perfect, but enough to judge component placement before building. A rendered version with color/spacing (same content) is available as a design artifact; ask if you want that link.

### Main menu — grown from 2 buttons to 5

```
┌ AppClub — Sistema de gestión del Club Social Paraiso ─────────┐
│                                                                 │
│   [👤 Gestionar Miembros]     [🧾 Transacciones]               │
│   [📅 Periodos]               [📊 Informes]                    │
│              [⚙ Ajustes]                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

Same grid idea as today, but five entries instead of two, one icon+label style instead of emoji-prefix matching, and dispatch by an explicit id per button rather than `button.startswith("🧑‍🤝‍🧑")` (finding 5).

### Gestionar Miembros — existing screen, redrawn

```
┌ AppClub — Gestionar Miembros ──────────────────────────────────┐
│ ← Volver   [ 🔍 Buscar miembros, email, id… ]  Límite: 0        │
│                                                     Filtros ▾   │
├──────────────────────────────────────────────────────────────┤
│ [+ Nuevo] [✎ Editar] [🗑 Eliminar] │ [↻ Refrescar] [⬇ Exportar] [🧾 Registrar] │
├──────────────────────────────────────────────────────────────┤
│ Núm. socio │ Nombre │ Apellidos       │ Teléfono    │ Email              │ Estado   │
│ 1002       │ Marta  │ Fernández Ruiz  │ 612 345 678 │ marta.fr@gmail.com │ Activo   │
│ 1015       │ Jorge  │ Domínguez Peña  │ 699 122 034 │ jorge.dp@hotmail…  │ Activo   │
│ 1021       │ Lucía  │ Salas Iglesias  │ 644 890 213 │ lucia.salas@gmail… │ Inactivo │
│ 1033       │ Antonio│ Reyes Molina    │ 655 302 771 │ a.reyes@yahoo.es   │ Activo   │
└──────────────────────────────────────────────────────────────┘
```

Top bar, toolbar, and table keep their current structure and behavior (search, límite, Filtros, sortable headers) — only the palette, spacing, and icon set change. The "Vistas" dropdown is **dropped** (decided — see `PLAN.md` §2.16): it's a generic raw multi-table browser that can currently show internal tables like `logs` and `saldos_socios` with no formatting, which doesn't belong in a screen for a non-technical end user. `socios` loads through a real, members-owned query instead; every other table gets its own purpose-built screen (Transacciones, Periods, Settings) rather than a shared dump.

### Transacciones — shared composition, new columns

```
┌ AppClub — Transacciones ───────────────────────────────────────┐
│ ← Volver   [ 🔍 Buscar por socio… ]        Periodo: Enero 2026 ▾│
├──────────────────────────────────────────────────────────────┤
│ [+ Nuevo movimiento] │ [↻ Refrescar] [⬇ Exportar]              │
├──────────────────────────────────────────────────────────────┤
│ Fecha │ Socio                  │ Tipo       │   Monto │ Método         │
│ 05/01 │ 1002 · Fernández Ruiz  │ Cargo      │  45,00€ │ Domiciliación  │
│ 07/01 │ 1015 · Domínguez Peña  │ Pago       │  45,00€ │ Efectivo       │
│ 12/01 │ 1033 · Reyes Molina    │ Reembolso  │ –20,00€ │ Transferencia  │
└──────────────────────────────────────────────────────────────┘
```

Reuses the exact top-bar/toolbar/table shape proposed for the shared "data screen" composition (§2 Structure) — only columns, filters, and toolbar actions change per domain. This is one of **two** entry points into transactions (decided — see `PLAN.md` §2.4): this standalone screen is for club-wide browsing/filtering by fecha/tipo/estado; the existing "Registrar" button in Gestionar Miembros stays as a quick shortcut that opens the same dialog with the socio pre-filled from the selected member row, instead of picking one here.

### Diálogo: Nuevo socio

```
┌ Nuevo miembro ──────────────┐
│ Núm. socio* │ 1041          │
│ Nombre*     │ Isabel        │
│ Apellidos*  │ Navarro Ortiz │
│ Teléfono    │ 611 220 984   │
│ Estado      │ activo ▾      │
│                              │
│           [Cancelar] [Aceptar] │
└──────────────────────────────┘
```

Same token set applied to `MemberDialog`'s existing fields (full form also has Email, Fecha de alta, Observaciones — trimmed here for space).

---

## 4. Summary — changes vs. stays

| Stays | Changes |
|---|---|
| PySide6 / Qt widgets as the framework | Hardcoded hex in `styles.py` → shared token module |
| SQLAlchemy + SQLite persistence | Black+gradient main menu / flat-grey members screen → one unified palette |
| `features/<domain>/` folder convention | `QStyle.SP_*` stock icons → a chosen icon set (`qtawesome`) |
| Spanish domain naming & UI text | Emoji-prefix button routing → explicit id/route dispatch |
| `QStandardItemModel` for table data | Fixed pixel sizing → layout-driven sizing + minimum size |
| | Dead QSS comment + `on_refresh` indentation bugs → fixed |
| | _New:_ keyboard-focus state, semantic warning/danger colors |
| | _New:_ extracted "data screen" composition for future features |
| | _New dependency:_ `openpyxl` for the already-present Exportar button |
| | "Vistas" multi-table dropdown → **removed** from Members, not added to Transacciones (`PLAN.md` §2.16) |
| | Transacciones gets **two** entry points: Members' existing "Registrar" (socio pre-filled) + a new standalone main-menu screen (`PLAN.md` §2.4) |
