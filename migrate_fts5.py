import sqlite3

DB_PATH = "journal.db"
con = sqlite3.connect(DB_PATH)
cur = con.cursor()

cur.execute("PRAGMA journal_mode=WAL;")

# Drop and recreate only if you're okay resetting the FTS index (not the base table).
# cur.execute("DROP TABLE IF EXISTS entries_fts")

# External-content FTS5 with prefix search (2–3 chars)
cur.execute("""
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
USING fts5(
  content, 
  content='entries',
  content_rowid='id',
  tokenize='porter unicode61',
  prefix='2 3'
);
""")

# Triggers: keep FTS in sync with entries
cur.executescript("""
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, NULL);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, content) VALUES('delete', old.id, NULL);
  INSERT INTO entries_fts(rowid, content) VALUES (new.id, new.content);
END;
""")

# Canonical backfill for external-content tables
# (Rebuilds the entire index from the 'entries' table)
cur.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild');")

con.commit()
con.close()

print("FTS5 migration complete.")
