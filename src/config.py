# src/config.py
import os
from pathlib import Path

# Root directory = project root (two levels up from here)
BASE_DIR = Path(__file__).resolve().parent.parent

# Data folder outside src/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database URL
DATABASE_URL = f"sqlite:///{DATA_DIR / 'club_manager.db'}"
