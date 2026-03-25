from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple


# Adapted from upstream core.query_parser.py

def _split_query_tokens(raw: str) -> Tuple[List[str], List[str]]:
    parts = str(raw or "").split()
    if not parts:
        return [], []

    positive_words: List[str] = []
    exclude_words: List[str] = []
    for token in parts:
        if token.startswith("-"):
            if len(token) > 1:
                exclude_words.append(token[1:])
            continue
        positive_words.append(token)
    return positive_words, exclude_words


def parse_tab_query(raw: str) -> Tuple[str, List[str]]:
    positive_words, exclude_words = _split_query_tokens(raw)
    db_keyword = positive_words[0] if positive_words else ""
    return db_keyword, exclude_words


def parse_search_query(raw: str) -> Tuple[str, List[str]]:
    positive_words, exclude_words = _split_query_tokens(raw)
    search_query = " ".join(positive_words)
    return search_query, exclude_words


def build_fetch_key(search_keyword: str, exclude_words: List[str]) -> str:
    normalized_keyword = (search_keyword or "").strip().lower()
    normalized_excludes = sorted(
        {
            word.strip().lower()
            for word in (exclude_words or [])
            if isinstance(word, str) and word.strip()
        }
    )
    return f"{normalized_keyword}|{'|'.join(normalized_excludes)}"


@dataclass(frozen=True)
class QueryIntent:
    raw_query: str
    search_query: str
    db_keyword: str
    exclude_words: List[str]
    fetch_key: str
    days: int | None
    limit: int


def detect_recent_days(raw: str) -> int | None:
    lowered = str(raw or "").lower()

    import re

    m = re.search(r"최근\s*(\d+)\s*일", raw)
    if m:
        return max(1, min(365, int(m.group(1))))
    m = re.search(r"(\d+)\s*일\s*(내|이내)", raw)
    if m:
        return max(1, min(365, int(m.group(1))))

    korean_map = {
        "오늘": 1,
        "금일": 1,
        "어제": 2,
        "최근": 7,
        "최신": 7,
        "이번주": 7,
        "이번 주": 7,
        "지난주": 14,
        "지난 주": 14,
        "한달": 30,
        "한 달": 30,
    }
    for token, days in korean_map.items():
        if token in raw:
            return days
    if "today" in lowered:
        return 1
    if "this week" in lowered or "recent" in lowered or "latest" in lowered:
        return 7
    return None


def clean_natural_query(raw: str) -> str:
    import re

    stripped = str(raw or "").strip()
    for token in ["뉴스", "브리핑", "찾아줘", "찾아 줘", "요약해줘", "요약해 줘", "검색해줘", "검색해 줘", "오늘", "금일", "어제", "최근", "최신", "이번주", "이번 주", "지난주", "지난 주"]:
        stripped = stripped.replace(token, " ")
    stripped = re.sub(r"\b(today|latest|recent|this week)\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\d+\s*일\s*(내|이내)?", " ", stripped)
    return " ".join(stripped.split())


def build_intent(raw_query: str, *, limit: int = 10, days: int | None = None) -> QueryIntent:
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
