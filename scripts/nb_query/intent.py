from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from nb_query.natural import clean_natural_query, detect_recent_days
from nb_query.tokens import build_fetch_key, parse_search_query, parse_tab_query


@dataclass(frozen=True)
class QueryIntent:
    raw_query: str
    search_query: str
    db_keyword: str
    exclude_words: List[str]
    fetch_key: str
    days: int | None
    limit: int


def build_intent(
    raw_query: str, *, limit: int = 10, days: int | None = None
) -> QueryIntent:
    cleaned = clean_natural_query(raw_query)
    detected_days = days if days is not None else detect_recent_days(raw_query)
    search_query, exclude_words = parse_search_query(cleaned)
    db_keyword, _ = parse_tab_query(cleaned)
    if not search_query:
        raise ValueError("최소 1개 이상의 일반 키워드가 필요합니다.")
    return QueryIntent(
        raw_query=raw_query,
        search_query=search_query,
        db_keyword=db_keyword or search_query,
        exclude_words=exclude_words,
        fetch_key=build_fetch_key(search_query, exclude_words),
        days=detected_days,
        limit=max(1, min(100, int(limit))),
    )


def cutoff_iso(days: int | None, now: datetime | None = None) -> str | None:
    if not days:
        return None
    base = now or datetime.now()
    return (base - timedelta(days=days)).isoformat(timespec="seconds")


__all__ = ["QueryIntent", "build_intent", "cutoff_iso"]
