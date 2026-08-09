# Architecture: app shell, UI chrome, and utils

Part of [ARCHITECTURE.md](../ARCHITECTURE.md)'s split — see that file for the index, and [CLAUDE.md](../CLAUDE.md) for project overview/commands/durable invariants. Covers `src/utils/`, `src/ui/styles.py`, `src/ui/main_window.py`, and `src/ui/views/`.

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
The home screen. Title label with a drop-shadow effect, then a 2-column `QGridLayout` of buttons built from a list of `(route_id, label, handler)` tuples:
- `("miembros", "🧑‍🤝‍🧑 Gestionar Miembros", show_members_view)` — navigates to the members screen.
- `("transacciones", "🧾 Transacciones", show_transactions_view)` — navigates to the standalone Transacciones screen (`features/transactions/view.py`).
- `("ajustes", "⚙️ Ajustes", show_settings_view)` — navigates to the Settings hub (`features/settings/menu_view.py`).

Each button's `objectName` is set to `f"menuButton_{route_id}"` and its `clicked` signal is connected directly to `handler(main_window)` — **decided (durable):** dispatch is by explicit handler reference, not by matching an emoji prefix parsed out of the button's label. The previous version did `if button.startswith("🧑‍🤝‍🧑"): ...` per button, which `UI_PROPOSAL.md` (finding #5) flagged as brittle and not scalable; it was replaced outright rather than extended when a third button (Transacciones) was added. If you add a new home-menu button, add a new `(route_id, label, handler)` tuple — don't reintroduce string-matching on the label.

Also defines `show_home()`, a convenience to switch the stack back to itself — but nothing currently calls it (back-navigation is instead handled by `MembersMenuView.on_back_to_main_menu`, which reaches into `main_window._stack`/`main_window._home` directly).
