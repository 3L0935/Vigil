"""SQLite storage for settings."""

import os
import shutil
import sqlite3
import threading
from pathlib import Path

from data_paths import DATA_DIR as _DATA_DIR, private_file
_DB_PATH = str(_DATA_DIR / "vigil.db")

# One-time migration from old source-dir location
_old_db = Path(__file__).parent / "writher.db"
if _old_db.exists() and not (_DATA_DIR / "vigil.db").exists():
    shutil.copy2(str(_old_db), _DB_PATH)

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH, check_same_thread=False)
    private_file(Path(_DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    for suffix in ("-wal", "-shm"):
        private_file(Path(_DB_PATH + suffix))
    return c


def init():
    """Create tables if they don't exist."""
    with _lock:
        c = _conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        c.commit()
        c.close()


# ── Settings ──────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    """Return a setting value, or *default* if not found."""
    with _lock:
        c = _conn()
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        c.close()
    return row["value"] if row else default


def save_setting(key: str, value: str):
    """Insert or update a setting."""
    with _lock:
        c = _conn()
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        c.commit()
        c.close()


def save_settings(values: dict[str, str]) -> None:
    """Commit a group of settings as one SQLite transaction."""
    with _lock:
        connection = _conn()
        try:
            connection.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [(key, str(value)) for key, value in values.items()],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
