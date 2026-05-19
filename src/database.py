"""SQLite database layer for clipboard history."""
import os
import sqlite3
import uuid
import time

DATA_DIR = os.path.join(os.environ["APPDATA"], "HistoryClipboard")
DB_PATH = os.path.join(DATA_DIR, "history.db")

os.makedirs(DATA_DIR, exist_ok=True)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=1000")
    return conn


def init_db():
    """Create tables and indexes if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS history (
                id              TEXT PRIMARY KEY,
                type            TEXT NOT NULL,
                text_content    TEXT,
                text_preview    TEXT,
                image_path      TEXT,
                thumbnail_path  TEXT,
                created_at      REAL NOT NULL,
                pinned          INTEGER NOT NULL DEFAULT 0,
                data_hash       TEXT NOT NULL,
                UNIQUE(data_hash)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_created
                ON history(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_history_pinned
                ON history(pinned, created_at DESC);
        """)


def upsert_item(item_type, text_content, text_preview, image_path, thumbnail_path, data_hash):
    """
    Insert a new clipboard item, or update timestamp if hash exists (dedup).
    """
    now = time.time()
    item_id = str(uuid.uuid4())

    with _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO history
               (id, type, text_content, text_preview,
                image_path, thumbnail_path, created_at, pinned, data_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (item_id, item_type, text_content, text_preview,
             image_path, thumbnail_path, now, data_hash)
        )

        if conn.total_changes == 0:
            conn.execute(
                "UPDATE history SET created_at = ? WHERE data_hash = ?",
                (now, data_hash)
            )
            row = conn.execute(
                "SELECT id FROM history WHERE data_hash = ?", (data_hash,)
            ).fetchone()
            if row:
                item_id = row[0]

        conn.commit()
        row = conn.execute(
            "SELECT * FROM history WHERE id = ?", (item_id,)
        ).fetchone()

    return _row_to_dict(row) if row else None


def get_all(limit=500):
    """Return all items, pinned first, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY pinned DESC, created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def search(query, limit=200):
    """Search text items by keyword."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM history
               WHERE type = 'text' AND text_content LIKE ?
               ORDER BY pinned DESC, created_at DESC LIMIT ?""",
            (f"%{query}%", limit)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_item(item_id):
    """Delete an item by id. Returns the deleted item for image cleanup."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM history WHERE id = ?", (item_id,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
            conn.commit()
    return _row_to_dict(row) if row else None


def toggle_pin(item_id):
    """Toggle pinned status. Returns updated item."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM history WHERE id = ?", (item_id,)
        ).fetchone()
        if row:
            new_val = 0 if row[7] else 1  # pinned is column 7 (0-indexed)
            conn.execute(
                "UPDATE history SET pinned = ? WHERE id = ?", (new_val, item_id)
            )
            conn.commit()
        row = conn.execute(
            "SELECT * FROM history WHERE id = ?", (item_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_settings():
    """Return all settings as a dict."""
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {k: v for k, v in rows}


def set_setting(key, value):
    """Set a single setting."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        conn.commit()


def cleanup_expired(retention_days):
    """Remove unpinned items older than retention_days. Returns deleted image paths."""
    cutoff = time.time() - (retention_days * 86400)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, image_path, thumbnail_path FROM history "
            "WHERE pinned = 0 AND created_at < ?",
            (cutoff,)
        ).fetchall()
        deleted = [(r[1], r[2]) for r in rows if r[1]]
        conn.execute(
            "DELETE FROM history WHERE pinned = 0 AND created_at < ?",
            (cutoff,)
        )
        conn.commit()
    return deleted


def _row_to_dict(row):
    return {
        "id": row[0],
        "type": row[1],
        "text_content": row[2],
        "text_preview": row[3],
        "image_path": row[4],
        "thumbnail_path": row[5],
        "created_at": row[6],
        "pinned": bool(row[7]),
        "data_hash": row[8],
    }
