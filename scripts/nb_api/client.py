from __future__ import annotations

import html
import re
import time
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Protocol

import requests

from nb_api.errors import format_naver_http_error, parse_naver_api_error
from nb_api.models import NewsItem

# Upstream: navernews-tabsearch core/naver_api.py (NAVER API HUB, v32.12.0).
# Legacy Developers Center endpoint (openapi.naver.com, X-Naver-Client-*)는
# 더 이상 유효하지 않으므로 API HUB 계약을 따른다.
API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
# 응답 형식. 공식 문서 기본값은 json이지만 서버 기본값에 의존하지 않고 명시한다.
# (공식 문서: format=json (default) | xml)
API_FORMAT = "json"
API_KEY_ID_HEADER = "X-NCP-APIGW-API-KEY-ID"
API_KEY_HEADER = "X-NCP-APIGW-API-KEY"
API_HUB_PRODUCT_URL = "https://www.ncloud.com/product/applicationService/naverApiHub"
API_HUB_GUIDE_URL = "https://guide.ncloud-docs.com/docs/apihub-use"
API_HUB_MIGRATION_URL = "https://guide.ncloud-docs.com/docs/apihub-migration"
MAX_RETRIES = 3

# 뉴스 검색 정렬. 문서: sim(정확도순, 기본값) | date(최신순).
# 이 스킬 기본값은 최신 기사 수집에 맞는 date이며, 호출 시 sim을 고를 수 있다.
ALLOWED_API_SORTS = ("date", "sim")
DEFAULT_API_SORT = "date"


def normalize_api_sort(value: object, fallback: str = DEFAULT_API_SORT) -> str:
    """검색 정렬 값을 date/sim으로 정규화한다."""
    text = str(value or "").strip().lower()
    if text in ALLOWED_API_SORTS:
        return text
    if str(fallback or "").strip().lower() in ALLOWED_API_SORTS:
        return str(fallback).strip().lower()
    return DEFAULT_API_SORT


class ResponseLike(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Dict[str, Any]: ...


class SessionLike(Protocol):
    def get(
        self, url: str, *, headers: Dict[str, str], params: Dict[str, Any], timeout: int
    ) -> ResponseLike: ...


def naver_auth_headers(client_id: str, client_secret: str) -> Dict[str, str]:
    """API HUB 호출용 게이트웨이 인증 헤더를 만든다."""
    return {
        API_KEY_ID_HEADER: str(client_id or "").strip(),
        API_KEY_HEADER: str(client_secret or "").strip(),
    }


RE_BOLD_TAGS = re.compile(r"</?b>")


def parse_pub_date(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().isoformat(timespec="seconds")
    except Exception:
        return None


def clean_item(item: Dict[str, Any]) -> NewsItem:
    title = html.unescape(RE_BOLD_TAGS.sub("", str(item.get("title", ""))))
    desc = html.unescape(RE_BOLD_TAGS.sub("", str(item.get("description", ""))))
    naver_link = str(item.get("link", "") or "")
    original_link = str(item.get("originallink", "") or "")
    if "news.naver.com" in naver_link:
        final_link = naver_link
    elif "news.naver.com" in original_link:
        final_link = original_link
    else:
        final_link = naver_link or original_link

    publisher = "정보 없음"
    if original_link:
        publisher = (
            urllib.parse.urlparse(original_link).netloc.replace("www.", "") or publisher
        )
    elif final_link:
        publisher = (
            "네이버뉴스"
            if "news.naver.com" in final_link
            else urllib.parse.urlparse(final_link).netloc.replace("www.", "")
        )
    return NewsItem(
        title=title,
        description=desc,
        link=final_link,
        original_link=original_link,
        publisher=publisher or "정보 없음",
        pub_date=str(item.get("pubDate", "") or ""),
        pub_date_iso=parse_pub_date(str(item.get("pubDate", "") or "")),
    )


def _retry_backoff_seconds(attempt: int) -> float:
    return min(8.0, 0.5 * (2 ** max(0, attempt)))


def fetch_news(
    *,
    client_id: str,
    client_secret: str,
    search_query: str,
    exclude_words: List[str],
    limit: int = 10,
    days: int | None = None,
    timeout: int = 15,
    session: SessionLike | None = None,
    max_retries: int = MAX_RETRIES,
    sort: str = DEFAULT_API_SORT,
) -> Dict[str, Any]:
    if not search_query.strip():
        raise ValueError("검색어가 비어 있습니다.")
    if not client_id.strip() or not client_secret.strip():
        raise ValueError("네이버 API 자격증명이 설정되지 않았습니다.")

    active_session = session or requests.Session()
    params = {
        "query": search_query,
        "display": min(max(limit, 10), 100),
        "start": 1,
        "sort": normalize_api_sort(sort),
        "format": API_FORMAT,
    }

    # Owner decision D3: NAVER API HUB URL이 정답. Legacy 개발자센터
    # (openapi.naver.com) 폴백 제거 — 해당 키는 더 이상 유효하지 않음.
    endpoint_candidates = [
        (API_URL, naver_auth_headers(client_id, client_secret)),
    ]

    last_resp: ResponseLike | None = None
    resp: ResponseLike | None = None
    for ep_url, ep_headers in endpoint_candidates:
        attempts = max(1, int(max_retries or 1))
        current_resp = active_session.get(
            ep_url, headers=ep_headers, params=params, timeout=timeout
        )
        for attempt in range(1, attempts):
            if current_resp.status_code == 200:
                break
            if not 500 <= int(current_resp.status_code or 0) < 600:
                break
            time.sleep(_retry_backoff_seconds(attempt - 1))
            current_resp = active_session.get(
                ep_url, headers=ep_headers, params=params, timeout=timeout
            )
        last_resp = current_resp
        if current_resp.status_code == 200:
            resp = current_resp
            break

    if resp is None or resp.status_code != 200:
        target_resp = resp or last_resp
        status = target_resp.status_code if target_resp else 500
        try:
            payload = target_resp.json() if target_resp else {}
            error_code, error_msg = parse_naver_api_error(payload)
        except Exception:
            error_code, error_msg = "", ""
            try:
                error_msg = f"HTTP {status}: {getattr(target_resp, 'text', '')[:200]}"
            except Exception:
                error_msg = f"HTTP {status}"
        raise RuntimeError(
            format_naver_http_error(status, error_code, error_msg or "알 수 없는 오류")
        )

    data = resp.json()
    exclude_words_lc = [w.lower() for w in exclude_words if w]
    cutoff = None
    if days:
        cutoff = datetime.now().astimezone().timestamp() - (days * 86400)

    items: List[NewsItem] = []
    filtered_out = 0
    too_old = 0
    for raw in data.get("items", []):
        item = clean_item(raw)
        text_blob = f"{item.title}\n{item.description}".lower()
        if exclude_words_lc and any(ex in text_blob for ex in exclude_words_lc):
            filtered_out += 1
            continue
        if cutoff is not None and item.pub_date_iso:
            try:
                if datetime.fromisoformat(item.pub_date_iso).timestamp() < cutoff:
                    too_old += 1
                    continue
            except Exception:
                pass
        items.append(item)
        if len(items) >= limit:
            break

    return {
        "query": search_query,
        "exclude_words": exclude_words,
        "days": days,
        "sort": params["sort"],
        "total": int(data.get("total", 0) or 0),
        "displayed": len(items),
        "filtered_out": filtered_out,
        "too_old": too_old,
        "items": [item.to_dict() for item in items],
        "raw_meta": {"lastBuildDate": data.get("lastBuildDate", "")},
    }


__all__ = [
    "ALLOWED_API_SORTS",
    "API_FORMAT",
    "API_HUB_GUIDE_URL",
    "API_HUB_MIGRATION_URL",
    "API_HUB_PRODUCT_URL",
    "API_KEY_HEADER",
    "API_KEY_ID_HEADER",
    "API_URL",
    "DEFAULT_API_SORT",
    "MAX_RETRIES",
    "ResponseLike",
    "SessionLike",
    "clean_item",
    "fetch_news",
    "naver_auth_headers",
    "normalize_api_sort",
    "parse_pub_date",
]
