
from pathlib import Path
from database.init_db import init_db
from ui.main_window import run_main_window

DB_PATH = Path("data/club_manager.db")

if not DB_PATH.exists():
    init_db()

if __name__ == "__main__":
	# Allows running this file directly for quick manual testing.
	raise SystemExit(run_main_window())
