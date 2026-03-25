from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterable, List

from _paths import DB_PATH, ensure_data_dir


SCHEMA = """
CREATE TABLE IF NOT EXISTS watch_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  raw_query TEXT NOT NULL,
  search_query TEXT NOT NULL,
  db_keyword TEXT NOT NULL,
  exclude_json TEXT NOT NULL,
  fetch_key TEXT NOT NULL,
  days INTEGER,
  limit_count INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_checked_at TEXT,
  last_new_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS seen_items (
  watch_id INTEGER NOT NULL,
  link TEXT NOT NULL,
  published_at TEXT,
  first_seen_at TEXT NOT NULL,
  PRIMARY KEY (watch_id, link),
  FOREIGN KEY (watch_id) REFERENCES watch_rules(id) ON DELETE CASCADE
);
"""


@contextmanager
def connect():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def list_rules() -> List[Dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, raw_query, search_query, db_keyword, exclude_json, fetch_key, days, limit_count, created_at, updated_at, last_checked_at, last_new_count FROM watch_rules ORDER BY name"
        ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "name": row[1],
                "raw_query": row[2],
                "search_query": row[3],
                "db_keyword": row[4],
                "exclude_words": json.loads(row[5]),
                "fetch_key": row[6],
                "days": row[7],
                "limit": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "last_checked_at": row[11],
                "last_new_count": row[12],
            }
        )
    return result


def add_rule(*, name: str, raw_query: str, search_query: str, db_keyword: str, exclude_words: List[str], fetch_key: str, days: int | None, limit: int) -> Dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO watch_rules(name, raw_query, search_query, db_keyword, exclude_json, fetch_key, days, limit_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, raw_query, search_query, db_keyword, json.dumps(exclude_words, ensure_ascii=False), fetch_key, days, limit, now, now),
        )
    return get_rule(name)


def get_rule(name_or_id: str | int) -> Dict[str, Any]:
    query = "SELECT id, name, raw_query, search_query, db_keyword, exclude_json, fetch_key, days, limit_count, created_at, updated_at, last_checked_at, last_new_count FROM watch_rules WHERE {} = ?"
    field = "id" if isinstance(name_or_id, int) or str(name_or_id).isdigit() else "name"
    with connect() as conn:
        row = conn.execute(query.format(field), (int(name_or_id) if field == "id" else name_or_id,)).fetchone()
    if not row:
        raise KeyError(f"watch rule not found: {name_or_id}")
    return {
        "id": row[0], "name": row[1], "raw_query": row[2], "search_query": row[3], "db_keyword": row[4],
        "exclude_words": json.loads(row[5]), "fetch_key": row[6], "days": row[7], "limit": row[8],
        "created_at": row[9], "updated_at": row[10], "last_checked_at": row[11], "last_new_count": row[12],
    }


def remove_rule(name_or_id: str | int) -> int:
    field = "id" if isinstance(name_or_id, int) or str(name_or_id).isdigit() else "name"
    with connect() as conn:
        cur = conn.execute(f"DELETE FROM watch_rules WHERE {field} = ?", (int(name_or_id) if field == 'id' else name_or_id,))
        return int(cur.rowcount or 0)


def mark_seen(watch_id: int, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now().isoformat(timespec="seconds")
    new_items: List[Dict[str, Any]] = []
    with connect() as conn:
        for item in items:
            link = str(item.get("link", "") or "").strip()
            if not link:
                continue
            exists = conn.execute("SELECT 1 FROM seen_items WHERE watch_id = ? AND link = ?", (watch_id, link)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO seen_items(watch_id, link, published_at, first_seen_at) VALUES (?, ?, ?, ?)",
                (watch_id, link, item.get("pub_date_iso"), now),
            )
            new_items.append(item)
        conn.execute(
            "UPDATE watch_rules SET last_checked_at = ?, last_new_count = ?, updated_at = updated_at WHERE id = ?",
            (now, len(new_items), watch_id),
        )
    return new_items
