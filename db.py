import sqlite3
from pathlib import Path

DB_PATH = Path("journal.db")


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_db():
    con = sqlite3.connect(
        DB_PATH, check_same_thread=False
    )  # what is it, why are we setting to False
    con.row_factory = dict_factory
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_entries_content ON entries(content)")
    con.commit()
    con.close()
