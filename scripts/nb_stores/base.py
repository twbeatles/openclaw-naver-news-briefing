from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, Iterator, List

from _paths import ensure_data_dir


@contextmanager
def sqlite_database(db_path: Path | str, schema: str, migrations: Dict[str, Dict[str, str]]) -> Iterator[sqlite3.Connection]:
    """스키마 생성 + 누락 컬럼 마이그레이션을 적용한 SQLite 연결을 제공한다."""
    ensure_data_dir()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema)
        for table, table_migrations in migrations.items():
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for column, sql in table_migrations.items():
                if column not in columns:
                    conn.execute(sql)
        yield conn
        conn.commit()
    finally:
        conn.close()


def normalize_tags(tags: Iterable[str] | None) -> List[str]:
    """태그 목록의 공백 제거 + 순서 유지 중복 제거."""
    seen = set()
    result: List[str] = []
    for tag in tags or []:
        value = str(tag or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = ["normalize_tags", "sqlite_database"]
