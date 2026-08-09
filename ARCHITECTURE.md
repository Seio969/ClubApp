# ARCHITECTURE.md

Index into this codebase's per-file/per-class architecture reference. [CLAUDE.md](CLAUDE.md) has the project overview, commands, and the condensed cross-cutting invariants that matter on almost any task; this file just routes to the right deep-dive doc under `architecture/` so a `Read` only pulls in the domain a task actually touches, not the whole reference.

| File | Covers |
|---|---|
| [architecture/database.md](architecture/database.md) | `src/config.py`, `src/main.py`, everything under `src/database/` (models, session, audit, seed_db, init_db, schema drift), `src/common/view_registry.py` |
| [architecture/members.md](architecture/members.md) | `src/features/members/` (menu_service, toolbar_service, menu_view, toolbar, dialog) — the Members screen |
| [architecture/settings.md](architecture/settings.md) | `src/features/settings/` (menu_view hub, plus the metodos_pago/, reglas_cobro/, reset/ and audit_log/ subpackages) — the Ajustes hub |
| [architecture/transactions.md](architecture/transactions.md) | `src/features/transactions/` (service, dialog, toolbar, view) — Transacciones screen + the Members "Registrar" shortcut's backing service |
| [architecture/ui-and-utils.md](architecture/ui-and-utils.md) | `src/ui/` (styles, main_window, menu_bar, main_menu_widget) and `src/utils/` (logger, exporters) |
| [architecture/testing.md](architecture/testing.md) | `tests/` — fixture gotchas and current coverage map |
| [architecture/cross-cutting.md](architecture/cross-cutting.md) | Full-detail version of patterns that span multiple domains (audit logging, soft-deletion, table→screen ownership, feature-folder shape) |

Directory tree with one-line-per-module orientation lives in CLAUDE.md's "Directory map" — use it to figure out which of the files above covers the module you're about to touch.
