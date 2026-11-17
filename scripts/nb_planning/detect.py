from __future__ import annotations

import re
from typing import List

from nb_query import clean_natural_query

from nb_planning.models import SchedulePlan

_MONITOR_WORDS = ["모니터링", "감시", "체크", "알림", "추적", "watch"]
_BRIEF_WORDS = ["브리핑", "요약", "정리", "보고"]
_GROUP_HINTS = ["묶", "그룹", "여러", "같이", "함께", "이랑", "하고", "랑"]
GROUP_HINTS = list(_GROUP_HINTS)
_TEMPLATE_HINTS = {
    "concise": ["간단", "짧게", "핵심만", "한눈에"],
    "analyst": ["분석", "인사이트", "시사점", "깊게"],
    "morning-briefing": ["아침", "출근", "오전 보고", "morning"],
    "watch-alert": ["알림", "alert", "실시간", "바로"],
}
_TIME_OF_DAY_HINTS = {
    "아침": "08:00",
    "오전": "09:00",
    "점심": "12:00",
    "오후": "15:00",
    "저녁": "18:00",
    "밤": "21:00",
    "새벽": "06:00",
}
_DAYS_OF_WEEK = {
    "월": "mon",
    "화": "tue",
    "수": "wed",
    "목": "thu",
    "금": "fri",
    "토": "sat",
    "일": "sun",
}
_DOW_CRON = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}


def normalize_request(raw: str) -> str:
    return re.sub(r"\s+", " ", str(raw or "").strip())


def slugify_korean(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(text or "").strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "news-plan"


def detect_action(raw: str) -> str:
    has_monitor = any(word in raw for word in _MONITOR_WORDS)
    has_brief = any(word in raw for word in _BRIEF_WORDS)
    if has_monitor and not has_brief:
        return "monitor"
    if has_brief and not has_monitor:
        return "briefing"
    if has_monitor and has_brief:
        return "monitor+briefing"
    return "briefing"


def strip_schedule_and_action_phrases(text: str) -> str:
    patterns = [
        r"\d+\s*시간(?:마다|간격)",
        r"\d+\s*분(?:마다|간격)",
        r"매일",
        r"매주\s*[월화수목금토일]요일?",
        r"(?:아침|오전|점심|오후|저녁|밤|새벽)\s*\d{1,2}(?::|시)?\s*\d{0,2}분?(?:\s*에)?",
        r"\d{1,2}(?::|시)\s*\d{0,2}분?(?:\s*에)?",
        r"실시간",
        r"수시로",
        r"계속",
        r"지속적으로",
        r"주기적으로",
        r"모니터링해줘|모니터링 해줘|모니터링",
        r"감시해줘|감시 해줘|감시",
        r"체크해줘|체크 해줘|체크",
        r"알림해줘|알림 해줘",
        r"브리핑해줘|브리핑 해줘",
        r"정리해줘|정리 해줘",
        r"요약해줘|요약 해줘",
    ]
    stripped = text
    for pattern in patterns:
        stripped = re.sub(pattern, " ", stripped)
    return normalize_request(stripped)


def normalize_query_order(query: str) -> str:
    parts = [part for part in str(query or "").split() if part]
    positives = [part for part in parts if not part.startswith("-")]
    negatives = [part for part in parts if part.startswith("-")]
    return " ".join(positives + negatives)


def extract_queries(raw: str) -> List[str]:
    text = strip_schedule_and_action_phrases(normalize_request(raw))
    split_pattern = r"\s*(?:,|/|\+|그리고|및|이랑|와|과|랑|하고)\s*"
    candidates = [
        part.strip() for part in re.split(split_pattern, text) if part.strip()
    ]
    queries: List[str] = []
    for candidate in candidates:
        cleaned = normalize_query_order(clean_natural_query(candidate))
        if cleaned:
            queries.append(cleaned)
    deduped: List[str] = []
    seen = set()
    for query in queries:
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped


def detect_explicit_time(text: str) -> str | None:
    prefixed = re.search(
        r"(아침|오전|오후|저녁|밤|새벽)\s*(\d{1,2})(?:[:시]\s*(\d{1,2}))?분?", text
    )
    if prefixed:
        prefix = prefixed.group(1)
        hour = int(prefixed.group(2))
        minute = int(prefixed.group(3) or 0)
        if prefix in {"오후", "저녁", "밤"} and hour < 12:
            hour += 12
        if prefix == "새벽" and hour == 12:
            hour = 0
        if prefix == "오전" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    plain = re.search(r"(\d{1,2})(?:[:시]\s*(\d{1,2}))?분?", text)
    if plain:
        return f"{int(plain.group(1)):02d}:{int(plain.group(2) or 0):02d}"
    return None


def detect_schedule(raw: str) -> SchedulePlan:
    text = normalize_request(raw)

    if re.search(r"실시간|수시로|계속|지속적으로", text):
        return SchedulePlan(
            kind="interval", label="15분마다", cron="*/15 * * * *", interval_minutes=15
        )

    every_n_hours = re.search(r"(\d+)\s*시간(?:마다|간격)", text)
    if every_n_hours:
        hours = max(1, int(every_n_hours.group(1)))
        minutes = hours * 60
        cron = (
            f"0 */{hours} * * *"
            if minutes >= 60 and minutes % 60 == 0
            else f"*/{minutes} * * * *"
        )
        return SchedulePlan(
            kind="interval",
            label=f"{hours}시간마다",
            cron=cron,
            interval_minutes=minutes,
        )

    every_n_minutes = re.search(r"(\d+)\s*분(?:마다|간격)", text)
    if every_n_minutes:
        minutes = max(1, int(every_n_minutes.group(1)))
        return SchedulePlan(
            kind="interval",
            label=f"{minutes}분마다",
            cron=f"*/{minutes} * * * *",
            interval_minutes=minutes,
        )

    weekly = re.search(r"매주\s*([월화수목금토일])요일?", text)
    if weekly:
        day = _DAYS_OF_WEEK[weekly.group(1)]
        time = detect_explicit_time(text) or next(
            (v for k, v in _TIME_OF_DAY_HINTS.items() if k in text), "08:00"
        )
        hh, mm = time.split(":")
        return SchedulePlan(
            kind="weekly",
            label=f"매주 {weekly.group(1)}요일 {time}",
            cron=f"{int(mm)} {int(hh)} * * {_DOW_CRON[day]}",
            time=time,
            days_of_week=[day],
        )

    if "매일" in text:
        time = detect_explicit_time(text) or next(
            (v for k, v in _TIME_OF_DAY_HINTS.items() if k in text), "08:00"
        )
        hh, mm = time.split(":")
        return SchedulePlan(
            kind="daily",
            label=f"매일 {time}",
            cron=f"{int(mm)} {int(hh)} * * *",
            time=time,
        )

    return SchedulePlan(kind="manual", label="수동 실행")


def detect_template(raw: str, action: str, schedule: SchedulePlan) -> str:
    for template, words in _TEMPLATE_HINTS.items():
        if any(word in raw for word in words):
            return template
    if action == "monitor":
        return "watch-alert"
    if schedule.kind == "daily":
        return "morning-briefing"
    return "concise"


def detect_briefing_focus(raw: str, template: str) -> str:
    if template == "morning-briefing":
        return "아침 브리핑"
    if any(word in raw for word in ["핵심만", "간단", "짧게"]):
        return "핵심 요약"
    if any(word in raw for word in ["분석", "시사점", "인사이트"]):
        return "분석형 정리"
    return "일반 브리핑"


def detect_watch_intent(raw: str, action: str) -> str:
    if "monitor" not in action:
        return "none"
    if any(word in raw for word in ["계속", "실시간", "수시로", "바로"]):
        return "continuous"
    if any(word in raw for word in ["모니터링", "감시", "체크", "알림"]):
        return "scheduled"
    return "manual"


def suggest_name(queries: List[str], action: str) -> str:
    base = queries[0] if queries else action
    suffix = "watch" if "monitor" in action else "brief"
    return slugify_korean(f"{base}-{suffix}")


__all__ = [
    "GROUP_HINTS",
    "detect_action",
    "detect_briefing_focus",
    "detect_explicit_time",
    "detect_schedule",
    "detect_template",
    "detect_watch_intent",
    "extract_queries",
    "normalize_query_order",
    "normalize_request",
    "slugify_korean",
    "strip_schedule_and_action_phrases",
    "suggest_name",
]
