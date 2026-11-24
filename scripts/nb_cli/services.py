from __future__ import annotations

from typing import Any, Dict

from nb_api import fetch_news
from nb_query import build_intent
from nb_stores.config_store import get_runtime_credentials
from nb_stores.watch_store import mark_seen

# 애플리케이션 서비스 계층: CLI 명령(cmd_*)은 argparse 변환만 맡고,
# 실제 조회/저장 흐름은 이 모듈 함수에 의존한다(DIP).


def _perform_live_check(query: str, *, limit: int = 1) -> Dict[str, Any]:
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    return fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=query,
        exclude_words=[],
        limit=limit,
        days=None,
        timeout=timeout,
    )


def run_search(
    query: str, *, limit: int, days: int | None, sort: str = "date"
) -> Dict[str, Any]:
    """원샷 검색을 실행하고 결과 payload를 반환한다(출력은 명령 계층 담당)."""
    intent = build_intent(query, limit=limit, days=days)
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    result = fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=intent.search_query,
        exclude_words=intent.exclude_words,
        limit=intent.limit,
        days=intent.days,
        timeout=timeout,
        sort=sort,
    )
    result["intent"] = {
        "db_keyword": intent.db_keyword,
        "fetch_key": intent.fetch_key,
        "raw_query": intent.raw_query,
    }
    return result


def _run_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    result = fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=rule["search_query"],
        exclude_words=rule["exclude_words"],
        limit=rule["limit"],
        days=rule.get("days"),
        timeout=timeout,
        sort=str(rule.get("sort", "date") or "date"),
    )
    new_items = mark_seen(rule["id"], result["items"])
    return {
        "rule": rule,
        "summary": {
            "query": result["query"],
            "total": result["total"],
            "displayed": result["displayed"],
            "new_count": len(new_items),
            "filtered_out": result["filtered_out"],
            "too_old": result["too_old"],
        },
        "new_items": new_items,
        "all_items": result["items"],
    }


def _run_query_entry(
    query: str,
    *,
    limit: int,
    days: int | None,
    sort: str = "date",
    group: Dict[str, Any] | None = None,
    label: str | None = None,
    context: str | None = None,
) -> Dict[str, Any]:
    intent = build_intent(query, limit=limit, days=days)
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    result = fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=intent.search_query,
        exclude_words=intent.exclude_words,
        limit=intent.limit,
        days=intent.days,
        timeout=timeout,
        sort=sort,
    )
    result["intent"] = {
        "db_keyword": intent.db_keyword,
        "fetch_key": intent.fetch_key,
        "raw_query": intent.raw_query,
    }
    return {
        "query": query,
        "search_query": intent.search_query,
        "exclude_words": intent.exclude_words,
        "days": intent.days,
        "group_name": group["name"] if group else None,
        "label": label or (group.get("label") if group else None),
        "tags": group.get("tags", []) if group else [],
        "context": context or (group.get("context") if group else None),
        "result": result,
    }


__all__ = ["_perform_live_check", "_run_query_entry", "_run_rule", "run_search"]
