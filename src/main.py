
from database.init_db import init_db
from ui.main_window import run_main_window

# Always run init_db() - not just when the DB file is missing. create_all(),
# _add_missing_columns() and seed_all() are all documented as safe/idempotent
# on every startup (see init_db.py), and a column added to an existing model
# (like Socio.es_titular) needs _add_missing_columns() to actually run on a
# developer's/user's pre-existing DB - gating this behind "file doesn't
# exist yet" meant it silently never applied for anyone who already had a
# data/club_manager.db, causing "no such column" crashes at first query.
init_db()

if __name__ == "__main__":
	# Allows running this file directly for quick manual testing.
	raise SystemExit(run_main_window())